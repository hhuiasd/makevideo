import os
import sys
import traceback
import multiprocessing
import argparse
import configparser
import random
import json
import subprocess
import logging
import datetime
import tempfile

# ========== 基础配置 ==========
def get_base_dir():
    """获取基础目录，优先使用当前目录，否则使用脚本所在目录的父目录"""
    current_dir = os.getcwd()
    
    # 检查当前目录是否有必需的子目录
    required_dirs = ['music', 'video', 'bin']
    has_required_dirs = all(os.path.exists(os.path.join(current_dir, d)) for d in required_dirs)
    
    if has_required_dirs:
        return current_dir
    else:
        # 如果当前目录没有必需的子目录，使用脚本所在目录的父目录
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            executable_dir = os.path.dirname(sys.executable)
            parent_dir = os.path.dirname(executable_dir)
            
            # 检查父目录是否有必需的子目录
            if all(os.path.exists(os.path.join(parent_dir, d)) for d in required_dirs):
                return parent_dir
            else:
                return executable_dir
        else:
            # 直接运行Python脚本
            return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

MUSIC_DIR = os.path.join(BASE_DIR, 'music')
VIDEO_DIR = os.path.join(BASE_DIR, 'video')

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')
CACHE_TYPE = config.get('Default', 'cache_type', fallback='disk')

if CACHE_TYPE == 'memory':
    CACHE_DIR = os.path.join('\\.\pipe', 'makevideo_cache')
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
    except:
        pass
    CACHE_TYPE = 'disk'
    CACHE_DIR = os.path.join(tempfile.gettempdir(), 'makevideo_cache')
else:
    CACHE_DIR = os.path.join(BASE_DIR, 'cache')

try:
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
except:
    CACHE_DIR = os.path.join(tempfile.gettempdir(), 'makevideo_cache')

OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
LOG_DIR = os.path.join(BASE_DIR, 'log')
FFMPEG_PATH = os.path.join(BASE_DIR, 'bin', 'ffmpeg.exe')
FFPROBE_PATH = os.path.join(BASE_DIR, 'bin', 'ffprobe.exe')

DEFAULT_VIDEO_WIDTH = 1280
DEFAULT_VIDEO_HEIGHT = 720

encoder_config = {
    'encoder': 'hevc_nvenc',
    'preset': 'p7',
    'quality': 26,
    'resolution': '1280x720',
    'gop': 120
}

logger = None

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


# ========== 日志系统 ==========
def setup_logger():
    global logger
    
    if logger is not None:
        return logger
    
    is_child_process = any('--multiprocessing' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('spawn' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('pipe_handle' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('parent_pid' in arg for arg in sys.argv)
    
    logger = logging.getLogger('MakeVideo')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    if not is_child_process:
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(LOG_DIR, f'makevideo_{timestamp}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    if hasattr(console_handler, 'set_encoding'):
        console_handler.set_encoding('utf-8')
    else:
        if sys.stdout and sys.stderr and sys.stdout.encoding != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    if not is_child_process:
        file_handler.setFormatter(formatter)
    
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    if not is_child_process:
        logger.info(f"日志文件: {os.path.abspath(log_file)}")
    
    return logger


def get_logger():
    global logger
    if logger is None:
        setup_logger()
    return logger


def ensure_directories():
    os.makedirs(MUSIC_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


# ========== 编码配置 ==========
def set_encoder_config(encoder, preset, quality, resolution, gop):
    global encoder_config
    encoder_config['encoder'] = encoder
    encoder_config['preset'] = preset
    encoder_config['quality'] = quality
    encoder_config['resolution'] = resolution
    encoder_config['gop'] = gop
    
    width, height = resolution.split('x')
    global DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT
    DEFAULT_VIDEO_WIDTH = int(width)
    DEFAULT_VIDEO_HEIGHT = int(height)


def get_video_encoder():
    global encoder_config
    
    encoder = encoder_config['encoder']
    preset = encoder_config['preset']
    quality = encoder_config['quality']
    gop = encoder_config['gop']
    
    if encoder == 'hevc_nvenc':
        return encoder, [
            '-preset', preset,
            '-cq', str(quality),
            '-g', str(gop),
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-movflags', '+faststart'
        ]
    elif encoder == 'libx265':
        return encoder, [
            '-preset', preset,
            '-crf', str(quality),
            '-g', str(gop),
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-movflags', '+faststart'
        ]
    elif encoder == 'hevc_qsv':
        return encoder, [
            '-preset', preset,
            '-global_quality', str(quality),
            '-g', str(gop),
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-movflags', '+faststart'
        ]
    else:
        return 'hevc_nvenc', [
            '-preset', 'p7',
            '-cq', '26',
            '-g', '240',
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-movflags', '+faststart'
        ]


# ========== 工具函数 ==========
def detect_gpu_acceleration():
    try:
        result = subprocess.run(
            [FFMPEG_PATH, '-hide_banner', '-encoders'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        encoders_output = result.stdout
        
        if 'hevc_nvenc' in encoders_output:
            return 'nvidia'
        elif 'h264_qsv' in encoders_output:
            return 'intel'
        else:
            return 'cpu'
    except:
        return 'cpu'


def get_media_duration(file_path):
    cmd = [
        FFPROBE_PATH,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if result.returncode != 0:
        return 0
    
    try:
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])
        return duration
    except Exception:
        return 0


def run_ffmpeg_command(cmd, description="FFmpeg命令"):
    logger = get_logger()
    try:
        cmd_str = ' '.join(cmd)
        logger.info(f"执行{description}: {cmd_str}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', shell=False, timeout=60)
        
        if result.returncode != 0:
            error_msg = f"{description}失败: {result.stderr}"
            logger.error(error_msg)
            return False
        
        logger.info(f"{description}成功")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"{description}执行超时")
        return False
    except Exception as e:
        logger.error(f"执行{description}时出错: {str(e)}")
        return False


# ========== MP3处理 ==========
def get_all_mp3_files():
    mp3_files = []
    if not os.path.exists(MUSIC_DIR):
        return mp3_files
    
    for filename in os.listdir(MUSIC_DIR):
        if filename.lower().endswith('.mp3'):
            mp3_files.append(filename)
    
    return mp3_files


def get_mp3_duration(mp3_file):
    mp3_path = os.path.join(MUSIC_DIR, mp3_file)
    return get_media_duration(mp3_path)


# ========== 视频切片 ==========
def get_all_video_files():
    video_files = []
    if not os.path.exists(VIDEO_DIR):
        return video_files
    
    for filename in os.listdir(VIDEO_DIR):
        if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            video_files.append(filename)
    
    return video_files


def slice_video(video_path, start_time, duration, output_path, skip_end=0):
    logger = get_logger()
    video_duration = get_media_duration(video_path)
    
    if video_duration <= 0:
        logger.error(f"视频文件无效或无法获取时长: {video_path}")
        return False
    
    end_time = video_duration - skip_end
    
    if start_time >= end_time:
        logger.warning(f"跳过时间设置无效: start={start_time}, end={end_time}")
        return False
    
    actual_start = start_time
    actual_duration = min(duration, end_time - actual_start)
    
    if actual_duration <= 0:
        logger.warning(f"切片时长无效: {actual_duration}")
        return False
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        FFMPEG_PATH,
        '-ss', str(actual_start),
        '-i', video_path,
        '-t', str(actual_duration),
        '-c:v', 'copy',
        '-an',
        '-y',
        output_path
    ]
    
    success = run_ffmpeg_command(cmd, "视频切片(无损)")
    
    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return True
    else:
        logger.error(f"切片文件无效: {output_path}")
        return False


def get_random_video(video_files, used_videos):
    unused_videos = [v for v in video_files if v not in used_videos]
    
    if unused_videos:
        return random.choice(unused_videos), False
    else:
        return random.choice(video_files), True


def create_random_slices(mp3_name, mp3_duration, skip_start=1, skip_end=0, min_slice=3, max_slice=5):
    logger = get_logger()
    video_files = get_all_video_files()
    
    if not video_files:
        logger.error("未找到视频文件")
        return []
    
    logger.info(f"开始为 {mp3_name} 创建切片")
    
    total_duration = 0
    slices = []
    used_videos = set()
    video_usage_count = {}
    max_attempts = 1000
    attempts = 0
    target_duration = mp3_duration + 3
    all_videos_used_once = False
    
    while total_duration < target_duration and attempts < max_attempts:
        attempts += 1
        
        video_file, is_reuse = get_random_video(video_files, used_videos)
        
        if is_reuse and not all_videos_used_once:
            all_videos_used_once = True
        
        video_path = os.path.join(VIDEO_DIR, video_file)
        video_duration = get_media_duration(video_path)
        
        remaining_needed = target_duration - total_duration
        slice_duration = 0
        
        if remaining_needed > 0:
            slice_duration = random.uniform(min_slice, max_slice)
            if remaining_needed > min_slice:
                slice_duration = min(slice_duration, remaining_needed)
            else:
                slice_duration = remaining_needed
            slice_duration = min(slice_duration, video_duration - skip_start - skip_end)
        
        if slice_duration <= 0:
            continue
        
        max_start_time = video_duration - skip_end - slice_duration
        actual_start = random.uniform(skip_start, max_start_time)
        
        slice_name = f"{os.path.splitext(mp3_name)[0]}_{len(slices)}.mkv"
        slice_path = os.path.join(CACHE_DIR, slice_name)
        
        if slice_video(video_path, actual_start, slice_duration, slice_path, skip_end):
            slices.append(slice_path)
            total_duration += slice_duration
            used_videos.add(video_file)
            video_usage_count[video_file] = video_usage_count.get(video_file, 0) + 1
    
    if total_duration < target_duration and slices:
        video_file, _ = get_random_video(video_files, used_videos)
        video_path = os.path.join(VIDEO_DIR, video_file)
        video_duration = get_media_duration(video_path)
        
        remaining_needed = target_duration - total_duration
        if remaining_needed > 0:
            slice_duration = min(remaining_needed, video_duration - skip_start - skip_end, max_slice)
            if slice_duration > 0:
                max_start_time = video_duration - skip_end - slice_duration
                actual_start = random.uniform(skip_start, max_start_time)
                
                slice_name = f"{os.path.splitext(mp3_name)[0]}_{len(slices)}.mkv"
                slice_path = os.path.join(CACHE_DIR, slice_name)
                
                if slice_video(video_path, actual_start, slice_duration, slice_path, skip_end):
                    slices.append(slice_path)
                    total_duration += slice_duration
                    used_videos.add(video_file)
                    video_usage_count[video_file] = video_usage_count.get(video_file, 0) + 1
    
    return slices


# ========== 视频合并 ==========
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


def merge_videos_with_transitions(slices, output_path, transition=True, transition_duration=0.6, resolution=None):
    if resolution is None:
        resolution = encoder_config['resolution']

    logger = get_logger()
    valid_slices = validate_slices(slices)
    if not valid_slices:
        logger.error("无有效切片")
        return False

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


def merge_with_xfade_filter(slices, output_path, transition_duration=0.8, resolution=None):
    if resolution is None:
        resolution = encoder_config['resolution']
    
    logger = get_logger()
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
            filter_complex.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p[v{i}];")
            filter_complex.append(f"[{i+1}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p[v{i+1}];")
            filter_complex.append(f"[v{i}][v{i+1}]xfade=transition={trans}:duration={actual_trans}:offset={offset}[o{i+1}];")
        else:
            filter_complex.append(f"[{i+1}:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p[v{i+1}];")
            filter_complex.append(f"[o{i}][v{i+1}]xfade=transition={trans}:duration={actual_trans}:offset={offset}[o{i+1}];")

        current_offset = offset

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
        '-crf', '10',
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


# ========== 最终处理 ==========
def finalize_video(video_path, mp3_file, output_path, 
                  encoder=None, preset=None, quality=None, 
                  resolution=None, gop=None, 
                  sharpen=True, sharpen_params='5:5:0.6'):
    logger = get_logger()
    mp3_path = os.path.join(MUSIC_DIR, mp3_file)
    
    if not os.path.exists(mp3_path):
        logger.error(f"MP3文件不存在: {mp3_file}")
        return False
    
    mp3_duration = get_media_duration(mp3_path)
    
    if mp3_duration <= 0:
        logger.error(f"无法获取MP3时长: {mp3_file}")
        return False
    
    logger.info(f"最终处理: 添加背景音乐并裁剪到 {mp3_duration:.2f}秒")
    
    if encoder and preset and quality and gop:
        original_config = encoder_config.copy()
        set_encoder_config(encoder, preset, quality, resolution, gop)
        
        encoder, encoder_params = get_video_encoder()
        
        set_encoder_config(
            original_config['encoder'], 
            original_config['preset'], 
            original_config['quality'], 
            original_config['resolution'], 
            original_config['gop']
        )
    else:
        encoder, encoder_params = get_video_encoder()
    
    fade_start = max(0, mp3_duration - 2)
    
    cmd = [
        FFMPEG_PATH,
        '-i', video_path,
        '-i', mp3_path,
        '-map', '0:v',
        '-map', '1:a',
    ]
    
    if sharpen:
        cmd.extend(['-vf', f'unsharp={sharpen_params}'])
    
    cmd.extend([
        '-c:v', encoder,
        *encoder_params,
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
    
    success = run_ffmpeg_command(cmd, "最终处理")
    
    if success and os.path.exists(output_path):
        output_size = os.path.getsize(output_path)
        logger.info(f"输出文件大小: {output_size / (1024*1024):.2f} MB")
    
    return success


# ========== 清理 ==========
def cleanup_cache():
    logger = get_logger()
    if not os.path.exists(CACHE_DIR):
        logger.info("缓存目录不存在，无需清理")
        return True
    
    try:
        file_count = 0
        total_size = 0
        
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                total_size += file_size
                os.remove(file_path)
                file_count += 1
        
        logger.info(f"清理缓存完成: 删除了 {file_count} 个文件，释放 {total_size / (1024*1024):.2f} MB 空间")
        return True
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        return False


def cleanup_specific_files(files):
    logger = get_logger()
    cleaned_count = 0
    for file_path in files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                cleaned_count += 1
        except Exception as e:
            logger.warning(f"清理文件失败: {file_path} - {e}")
    
    logger.info(f"清理了 {cleaned_count} 个临时文件")
    return cleaned_count


def cleanup_all():
    cleanup_cache()


# ========== 主处理逻辑 ==========
def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    
    skip_start = float(config.get('Default', 'skip_start', fallback=2))
    skip_end = float(config.get('Default', 'skip_end', fallback=0))
    min_slice = float(config.get('Default', 'min_slice', fallback=2))
    max_slice = float(config.get('Default', 'max_slice', fallback=4))
    
    encoder = config.get('Default', 'encoder', fallback='hevc_nvenc')
    preset = config.get('Default', 'preset', fallback='p7')
    quality = int(config.get('Default', 'quality', fallback=28))
    resolution = config.get('Default', 'resolution', fallback='1280x720')
    gop = int(config.get('Default', 'gop', fallback=120))
    
    sharpen = config.getboolean('Default', 'sharpen', fallback=False)
    sharpen_params = config.get('Default', 'sharpen_params', fallback='5:5:0.6')
    
    transition = config.getboolean('Default', 'transition', fallback=True)
    transition_duration = float(config.get('Default', 'transition_duration', fallback=0.7))
    
    cache_type = config.get('Default', 'cache_type', fallback='disk')
    
    return {
        'skip_start': skip_start,
        'skip_end': skip_end,
        'min_slice': min_slice,
        'max_slice': max_slice,
        'encoder': encoder,
        'preset': preset,
        'quality': quality,
        'resolution': resolution,
        'gop': gop,
        'sharpen': sharpen,
        'sharpen_params': sharpen_params,
        'transition': transition,
        'transition_duration': transition_duration,
        'cache_type': cache_type
    }


def process_single_mp3(mp3_file, skip_start, skip_end, min_slice, max_slice, 
                      encoder, preset, quality, resolution, gop, 
                      sharpen=True, sharpen_params='5:5:0.8', 
                      transition=True, transition_duration=0.6):
    logger = get_logger()
    try:
        logger.info(f"处理音乐: {mp3_file}")
        logger.info("-" * 60)
        
        mp3_duration = get_mp3_duration(mp3_file)
        
        if mp3_duration <= 0:
            logger.warning(f"跳过无效的MP3文件: {mp3_file}")
            return False, mp3_file
        
        logger.info(f"MP3时长: {mp3_duration:.2f}秒")
        
        logger.info("步骤1: 为音乐创建视频切片...")
        slices = create_random_slices(
            mp3_file, mp3_duration, 
            skip_start=skip_start, 
            skip_end=skip_end, 
            min_slice=min_slice, 
            max_slice=max_slice
        )
        
        if not slices:
            logger.error(f"无法为 {mp3_file} 创建足够的切片")
            cleanup_specific_files(slices)
            return False, mp3_file
        
        temp_output = os.path.join(CACHE_DIR, f"temp_{os.path.splitext(mp3_file)[0]}_{os.getpid()}.mp4")
        
        logger.info("步骤2: 合并视频并添加转场...")
        if not merge_videos_with_transitions(slices, temp_output, 
                                          transition=transition, 
                                          transition_duration=transition_duration,
                                          resolution=resolution):
            logger.error("合并视频失败")
            cleanup_specific_files(slices)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False, mp3_file
        
        output_name = f"{os.path.splitext(mp3_file)[0]}.mp4"
        output_path = os.path.join('output', output_name)
        
        logger.info("步骤3: 最终处理（添加背景音乐并编码）...")
        if finalize_video(temp_output, mp3_file, output_path, 
                         encoder=encoder, preset=preset, quality=quality, 
                         resolution=resolution, gop=gop, 
                         sharpen=sharpen, sharpen_params=sharpen_params):
            logger.info(f"成功生成: {output_path}")
            cleanup_specific_files(slices)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return True, mp3_file
        else:
            logger.error(f"最终处理失败: {mp3_file}")
            cleanup_specific_files(slices)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False, mp3_file
            
    except Exception as e:
        error_msg = f"处理 {mp3_file} 时出错: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, mp3_file


def process_video_mixing(config):
    logger = get_logger()
    try:
        logger.info("="*60)
        logger.info("视频快速混剪项目")
        logger.info("="*60)
        
        ensure_directories()
        
        if not os.path.exists(FFMPEG_PATH) or not os.path.exists(FFPROBE_PATH):
            error_msg = "错误: 未找到FFmpeg工具，请确保bin目录下有ffmpeg.exe和ffprobe.exe"
            logger.error(error_msg)
            return False
        
        gpu_type = detect_gpu_acceleration()
        logger.info(f"检测到GPU加速: {gpu_type}")
        
        mp3_files = get_all_mp3_files()
        if not mp3_files:
            error_msg = "错误: 未找到MP3文件，请在music目录中添加MP3文件"
            logger.error(error_msg)
            return False
        
        video_files = get_all_video_files()
        if not video_files:
            error_msg = "错误: 未找到视频文件，请在video目录中添加视频文件"
            logger.error(error_msg)
            return False
        
        logger.info(f"找到 {len(mp3_files)} 个MP3文件和 {len(video_files)} 个视频文件")
        logger.info(f"处理参数: 跳过开头={config['skip_start']}秒, 跳过结尾={config['skip_end']}秒, 切片时长={config['min_slice']}-{config['max_slice']}秒")
        logger.info(f"缓存类型: {config['cache_type']}")
        logger.info("")
        
        pool_size = 1
        logger.info(f"使用 {pool_size} 个进程处理")
        logger.info("")
        
        encoder = config['encoder']
        preset = config['preset']
        quality = config['quality']
        resolution = config['resolution']
        gop = config['gop']
        
        tasks = [(mp3_file, config['skip_start'], config['skip_end'], config['min_slice'], config['max_slice'], 
                 encoder, preset, quality, resolution, gop, 
                 config['sharpen'], config['sharpen_params'], 
                 config['transition'], config['transition_duration']) for mp3_file in mp3_files]
        
        results = []
        for task in tasks:
            result = process_single_mp3(*task)
            results.append(result)
        
        successful_outputs = []
        failed_outputs = []
        for success, mp3_file in results:
            if success:
                successful_outputs.append(mp3_file)
            else:
                failed_outputs.append(mp3_file)
        
        logger.info("\n" + "="*60)
        logger.info("处理总结")
        logger.info("="*60)
        logger.info(f"成功: {len(successful_outputs)} 个")
        logger.info(f"失败: {len(failed_outputs)} 个")
        
        if successful_outputs:
            logger.info("\n成功生成的视频:")
            for output in successful_outputs:
                logger.info(f"  ✓ {output}")
        
        if failed_outputs:
            logger.warning("\n失败的音乐:")
            for output in failed_outputs:
                logger.warning(f"  ✗ {output}")
        
        cleanup_report(successful_outputs, mp3_files)
        
        logger.info("\n清理缓存...")
        cleanup_cache()
        
        logger.info("\n所有处理完成！")
        return True
        
    except Exception as e:
        error_msg = f"\n程序运行出错: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        cleanup_all()
        return False


def cleanup_report(output_files, mp3_files):
    print("\n" + "="*50)
    print("处理完成报告")
    print("="*50)
    
    print(f"\n处理的MP3文件数量: {len(mp3_files)}")
    for mp3_file in mp3_files:
        print(f"  - {mp3_file}")
    
    print(f"\n生成的视频文件数量: {len(output_files)}")
    total_size = 0
    for output_file in output_files:
        output_path = os.path.join(OUTPUT_DIR, output_file)
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            total_size += file_size
            print(f"  - {output_file} ({file_size / (1024*1024):.2f} MB)")
    
    print(f"\n总输出大小: {total_size / (1024*1024):.2f} MB")
    print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print("="*50 + "\n")


def main(args=None):
    setup_logger()
    logger = get_logger()
    
    is_child_process = any('--multiprocessing' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('spawn' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('pipe_handle' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('parent_pid' in arg for arg in sys.argv)
    
    if is_child_process:
        return
    
    try:
        default_config = load_config()
        
        parser = argparse.ArgumentParser(description='视频快速混剪工具')
        parser.add_argument('skip_start', nargs='?', type=float, default=default_config['skip_start'], help='跳过视频开头秒数')
        parser.add_argument('skip_end', nargs='?', type=float, default=default_config['skip_end'], help='跳过视频结尾秒数')
        parser.add_argument('min_slice', nargs='?', type=float, default=default_config['min_slice'], help='最小切片时长秒数')
        parser.add_argument('max_slice', nargs='?', type=float, default=default_config['max_slice'], help='最大切片时长秒数')
        parser.add_argument('--encoder', type=str, default=default_config['encoder'], 
                           choices=['hevc_nvenc', 'libx265', 'hevc_qsv'],
                           help='视频编码器')
        parser.add_argument('--preset', type=str, default=default_config['preset'], help='编码预设')
        parser.add_argument('--quality', type=int, default=default_config['quality'], help='质量参数(CQ/CRF)')
        parser.add_argument('--resolution', type=str, default=default_config['resolution'], help='输出分辨率')
        parser.add_argument('--gop', type=int, default=default_config['gop'], help='GOP大小')
        parser.add_argument('--sharpen', type=lambda x: x.lower() == 'true', default=default_config['sharpen'], help='是否启用锐化滤镜')
        parser.add_argument('--sharpen-params', type=str, default=default_config['sharpen_params'], help='锐化滤镜参数')
        parser.add_argument('--transition', type=lambda x: x.lower() == 'true', default=default_config['transition'], help='是否启用转场特效')
        parser.add_argument('--transition-duration', type=float, default=default_config['transition_duration'], help='转场时长(秒)')
        parser.add_argument('--cache-type', type=str, choices=['memory', 'disk'], default='disk', help='缓存类型')
        
        if args:
            filtered_args = []
            for arg in args:
                if '=' not in arg and not arg.startswith('--multiprocessing'):
                    filtered_args.append(arg)
            args = parser.parse_args(filtered_args)
        else:
            filtered_args = []
            for arg in sys.argv[1:]:
                if '=' not in arg and not arg.startswith('--multiprocessing'):
                    filtered_args.append(arg)
            args = parser.parse_args(filtered_args)
        
        set_encoder_config(args.encoder, args.preset, args.quality, args.resolution, args.gop)
        
        logger.info(f"编码配置: 编码器={args.encoder}, 预设={args.preset}, 质量={args.quality}, 分辨率={args.resolution}, GOP={args.gop}")
        logger.info(f"锐化配置: 启用={args.sharpen}, 参数={args.sharpen_params}")
        logger.info(f"转场配置: 启用={args.transition}, 时长={args.transition_duration}秒")
        logger.info(f"切片参数: 跳过开头={args.skip_start}秒, 跳过结尾={args.skip_end}秒, 切片时长={args.min_slice}-{args.max_slice}秒")
        
        config = {
            'skip_start': args.skip_start,
            'skip_end': args.skip_end,
            'min_slice': args.min_slice,
            'max_slice': args.max_slice,
            'encoder': args.encoder,
            'preset': args.preset,
            'quality': args.quality,
            'resolution': args.resolution,
            'gop': args.gop,
            'sharpen': args.sharpen,
            'sharpen_params': args.sharpen_params,
            'transition': args.transition,
            'transition_duration': args.transition_duration,
            'cache_type': args.cache_type
        }
        
        process_video_mixing(config)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        cleanup_all()
        sys.exit(0)
    except Exception as e:
        error_msg = f"程序运行出错: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        cleanup_all()
        sys.exit(1)


if __name__ == "__main__":
    main()
