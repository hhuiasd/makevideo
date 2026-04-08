import os
import random
from utils import CACHE_DIR, FFMPEG_PATH, run_ffmpeg_command, get_logger

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
# 【关键】完全跳过标准化，不做任何预处理编码
# ==============================================
def normalize_slices(slices):
    logger = get_logger()
    logger.info("✅ 无损模式：跳过标准化，不压缩、不编码")
    return slices

def merge_videos_with_transitions(slices, output_path, transition=True, transition_duration=0.6, resolution=None):
    if resolution is None:
        from utils import encoder_config
        resolution = encoder_config['resolution']

    logger = get_logger()
    valid_slices = validate_slices(slices)
    if not valid_slices:
        logger.error("无有效切片")
        return False

    # 直接使用原始切片，不经过任何编码
    final_slices = valid_slices

    if len(final_slices) == 1:
        import shutil
        shutil.copy2(final_slices[0], output_path)
        return True

    if transition:
        success = merge_with_xfade_filter(final_slices, output_path, transition_duration, resolution)
    else:
        success = merge_videos_simple(final_slices, output_path)

    return success

# ==============================================
# 【终极正确】所有操作 一步 完成，只编码一次
# 缩放 + 裁剪 + 帧率 + 转场 → 全部一次搞定
# 完全无二次压缩！
# ==============================================
def merge_with_xfade_filter(slices, output_path, transition_duration=0.8, resolution=None):
    if resolution is None:
        from utils import encoder_config
        resolution = encoder_config['resolution']
    logger = get_logger()
    from utils import get_media_duration
    durations = [get_media_duration(s) for s in slices]
    width, height = resolution.split('x')

    filter_complex = []
    current_offset = 0

    for i in range(len(slices)-1):
        trans = random.choice(TRANSITIONS)
        dur = durations[i]
        next_dur = durations[i+1]
        actual_trans = min(transition_duration, dur*0.3, next_dur*0.3)
        actual_trans = max(0.3, actual_trans)
        offset = current_offset + dur - actual_trans

        if i == 0:
            # 第一个片段：缩放 + 帧率
            filter_complex.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p[v{i}];")
            # 第二个片段：缩放 + 帧率
            filter_complex.append(f"[{i+1}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p[v{i+1}];")
            # 转场
            filter_complex.append(f"[v{i}][v{i+1}]xfade=transition={trans}:duration={actual_trans}:offset={offset}[o{i+1}];")
        else:
            # 后续片段只需要处理新进来的片段
            filter_complex.append(f"[{i+1}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p[v{i+1}];")
            filter_complex.append(f"[o{i}][v{i+1}]xfade=transition={trans}:duration={actual_trans}:offset={offset}[o{i+1}];")

        current_offset = offset

    # 拼接滤镜
    final_filter = "".join(filter_complex).rstrip(";")
    out_label = f"[o{len(slices)-1}]"

    cmd = [FFMPEG_PATH, '-y']
    for s in slices:
        cmd.extend(['-i', s])

    cmd.extend([
        '-filter_complex', final_filter,
        '-map', out_label,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '10',       # 极高画质，几乎无损
        '-an',
        '-y',
        output_path
    ])

    return run_ffmpeg_command(cmd, "✅ 合并转场【仅编码一次 | 无二次压缩】")

def merge_videos_simple(slices, output_path):
    logger = get_logger()
    concat = os.path.join(CACHE_DIR, 'concat.txt')
    with open(concat, 'w', encoding='utf-8') as f:
        for s in slices:
            f.write(f"file '{os.path.abspath(s)}'\n")

    cmd = [
        FFMPEG_PATH, '-f', 'concat', '-safe', '0', '-i', concat,
        '-c:v', 'copy',
        '-an',
        '-y', output_path
    ]

    res = run_ffmpeg_command(cmd, "简单合并")
    os.remove(concat)
    return res

def cleanup_normalized_slices(slices):
    pass