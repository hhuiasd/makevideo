import os
import random
from utils import FFMPEG_PATH, run_ffmpeg_command, get_logger

TRANSITIONS = [
    'fade', 'wipeleft', 'wiperight', 'wipeup', 'wipedown',
    'slideleft', 'slideright', 'slideup', 'slidedown',
    'circlecrop', 'rectcrop', 'distance', 'fadeblack', 'fadewhite',
    'radial', 'smoothleft', 'smoothright', 'smoothup', 'smoothdown',
    'circleopen', 'circleclose', 'vertopen', 'vertclose',
    'horzopen', 'horzclose', 'dissolve', 'pixelize',
    'diagtl', 'diagtr', 'diagbl', 'diagbr',
    'hlslice', 'hrslice', 'vuslice', 'vdslice',
    'hblur', 'fadegrays', 'wipetl', 'wipetr', 'wipebl', 'wipebr',
    'squeezeh', 'squeezev', 'zoomin', 'fadefast', 'fadeslow',
    'hlwind', 'hrwind', 'vuwind', 'vdwind',
    'coverleft', 'coverright', 'coverup', 'coverdown',
    'revealleft', 'revealright', 'revealup', 'revealdown'
]

def validate_slices(slices):
    valid_slices = []
    logger = get_logger()
    for slice_path in slices:
        if slice_path:
            abs_path = os.path.abspath(slice_path)
            if os.path.exists(abs_path) and os.path.getsize(abs_path) > 1000:
                valid_slices.append(abs_path)
            else:
                logger.warning(f"跳过无效切片: {abs_path}")
    return valid_slices

# ==============================================
# 所有操作 一步 完成，只编码一次
# 切片 → xfade转场(+锐化) → 音频 → 编码 → 输出
# 无中间 temp 文件、无双重编码
# ==============================================
def merge_all_in_one(slices, mp3_path, mp3_duration, output_path,
                     transition=True, transition_duration=0.6, resolution=None,
                     sharpen=False, sharpen_params='5:5:0.6',
                     encoder='hevc_nvenc', encoder_params=None):
    if resolution is None:
        from utils import encoder_config
        resolution = encoder_config['resolution']
    logger = get_logger()
    from utils import get_media_duration

    valid_slices = validate_slices(slices)
    if not valid_slices:
        logger.error("无有效切片")
        return False

    if not os.path.exists(mp3_path):
        logger.error(f"MP3文件不存在: {mp3_path}")
        return False

    width, height = resolution.split('x')
    fade_start = max(0, mp3_duration - 2)
    audio_index = len(valid_slices)  # 音频在切片之后

    # ========== 构建 filter_complex ==========
    filter_parts = []
    out_label = None

    if len(valid_slices) == 1 or not transition:
        # --- 路径 B/C：无转场 ---
        # 每个切片: scale+crop+fps+强制方形像素(setsar=1)+format
        for i in range(len(valid_slices)):
            filter_parts.append(
                f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps=30,setsar=1,format=yuv420p[v{i}];"
            )
        if len(valid_slices) == 1:
            # 单切片，跳过 concat，直接到 sharpen
            out_label = "[v0]"
        else:
            # 多切片 concat
            concat_inputs = "".join(f"[v{i}]" for i in range(len(valid_slices)))
            filter_parts.append(f"{concat_inputs}concat=n={len(valid_slices)}:v=1:a=0[cc];")
            out_label = "[cc]"
    else:
        # --- 路径 A：xfade 转场（复用现有逻辑） ---
        durations = [get_media_duration(s) for s in valid_slices]
        current_offset = 0

        for i in range(len(valid_slices) - 1):
            trans = random.choice(TRANSITIONS)
            dur = durations[i]
            next_dur = durations[i + 1]
            actual_trans = min(transition_duration, dur * 0.3, next_dur * 0.3)
            actual_trans = max(0.3, actual_trans)
            offset = current_offset + dur - actual_trans

            if i == 0:
                filter_parts.append(
                    f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},fps=30,setsar=1,format=yuv420p[v0];"
                )
                filter_parts.append(
                    f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},fps=30,setsar=1,format=yuv420p[v1];"
                )
                filter_parts.append(
                    f"[v0][v1]xfade=transition={trans}:duration={actual_trans}:offset={offset}[o1];"
                )
            else:
                filter_parts.append(
                    f"[{i+1}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},fps=30,setsar=1,format=yuv420p[v{i+1}];"
                )
                filter_parts.append(
                    f"[o{i}][v{i+1}]xfade=transition={trans}:duration={actual_trans}:offset={offset}[o{i+1}];"
                )
            current_offset = offset

        out_label = f"[o{len(valid_slices) - 1}]"

    # ========== 锐化（嵌入 filter_complex） ==========
    if sharpen:
        filter_parts.append(f"{out_label}unsharp={sharpen_params}[outv];")
        out_label = "[outv]"

    final_filter = "".join(filter_parts).rstrip(";")

    # ========== 构建 FFmpeg 命令 ==========
    cmd = [FFMPEG_PATH, '-y']
    for s in valid_slices:
        cmd.extend(['-i', s])
    cmd.extend(['-i', mp3_path])

    cmd.extend(['-filter_complex', final_filter])
    cmd.extend(['-map', out_label, '-map', f'{audio_index}:a'])

    cmd.extend(['-c:v', encoder])
    if encoder_params:
        cmd.extend(encoder_params)

    cmd.extend([
        '-c:a', 'aac',
        '-b:a', '128k',
        '-t', str(mp3_duration),
        '-af', f'afade=t=out:st={fade_start}:d=2',
        '-max_interleave_delta', '100M',
        '-async', '1',
        '-vsync', '1',
        '-y',
        output_path
    ])

    success = run_ffmpeg_command(cmd, "✅ 一步编码【合并+转场+音频+编码 | 只编码一次】")

    if success and os.path.exists(output_path):
        output_size = os.path.getsize(output_path)
        logger.info(f"输出文件大小: {output_size / (1024*1024):.2f} MB")

    return success
