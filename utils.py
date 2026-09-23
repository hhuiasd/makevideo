import os
import subprocess
import json
import logging
import datetime
import tempfile

# 获取应用程序的基本目录
# 当使用PyInstaller打包时，sys._MEIPASS会指向临时提取目录
# 否则，使用当前文件所在的目录
import sys
if getattr(sys, 'frozen', False):
    # 打包后的可执行文件
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 直接运行Python脚本
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MUSIC_DIR = os.path.join(BASE_DIR, 'music')
VIDEO_DIR = os.path.join(BASE_DIR, 'video')
# 缓存设置
CACHE_TYPE = 'memory'  # 'memory' 或 'disk' 默认为memory，提高处理速度

# 缓存目录
if CACHE_TYPE == 'memory':
    # 使用内存映射文件系统
    CACHE_DIR = os.path.join('\\.\pipe', 'makevideo_cache')
    try:
        # 尝试创建内存映射目录
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
    except:
        # 如果失败，回退到临时目录
        CACHE_TYPE = 'disk'
        CACHE_DIR = os.path.join(tempfile.gettempdir(), 'makevideo_cache')
else:
    # 使用磁盘缓存
    CACHE_DIR = os.path.join(BASE_DIR, 'cache')

# 确保缓存目录存在
try:
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
except:
    # 如果失败，回退到临时目录
    CACHE_DIR = os.path.join(tempfile.gettempdir(), 'makevideo_cache')

OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
LOG_DIR = os.path.join(BASE_DIR, 'log')
FFMPEG_PATH = os.path.join(BASE_DIR, 'bin', 'ffmpeg.exe')
FFPROBE_PATH = os.path.join(BASE_DIR, 'bin', 'ffprobe.exe')

DEFAULT_VIDEO_WIDTH = 1280
DEFAULT_VIDEO_HEIGHT = 720
DEFAULT_VIDEO_CODEC = 'hevc_nvenc'
DEFAULT_AUDIO_CODEC = 'aac'

logger = None

encoder_config = {
    'encoder': 'hevc_nvenc',
    'preset': 'p7',
    'quality': 26,
    'resolution': '1280x720',
    'gop': 120
}

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

def set_cache_type(cache_type):
    """设置缓存类型
    
    Args:
        cache_type: 'memory' 或 'disk'
    """
    global CACHE_TYPE, CACHE_DIR
    CACHE_TYPE = cache_type
    
    if CACHE_TYPE == 'memory':
        # 使用内存映射文件系统
        CACHE_DIR = os.path.join('\\.\pipe', 'makevideo_cache')
        try:
            # 尝试创建内存映射目录
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)
            logger = get_logger()
            logger.info(f"内存映射目录创建成功: {CACHE_DIR}")
        except Exception as e:
            # 如果失败，回退到临时目录
            CACHE_TYPE = 'disk'
            CACHE_DIR = os.path.join(tempfile.gettempdir(), 'makevideo_cache')
            logger = get_logger()
            logger.warning(f"内存映射目录创建失败: {str(e)}，回退到临时目录: {CACHE_DIR}")
    else:
        # 使用磁盘缓存
        CACHE_DIR = os.path.join('cache')
        logger = get_logger()
        logger.info(f"设置磁盘缓存目录: {CACHE_DIR}")
    
    # 确保缓存目录存在
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            logger = get_logger()
            logger.info(f"缓存目录创建成功: {CACHE_DIR}")
        else:
            logger = get_logger()
            logger.info(f"缓存目录已存在: {CACHE_DIR}")
    except Exception as e:
        # 如果失败，回退到临时目录
        CACHE_DIR = os.path.join(tempfile.gettempdir(), 'makevideo_cache')
        logger = get_logger()
        logger.warning(f"缓存目录创建失败: {str(e)}，回退到临时目录: {CACHE_DIR}")

    logger = get_logger()
    logger.info(f"缓存类型设置为: {CACHE_TYPE}, 缓存目录: {CACHE_DIR}")

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
            '-tune', 'hq',
            '-spatial-aq', '1',
            '-temporal-aq', '1',
            '-rc-lookahead', '32',
            '-bf', '4',
            '-b_ref_mode', 'middle',
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-movflags', '+faststart'
        ]
    elif encoder == 'h264_nvenc':
        return encoder, [
            '-preset', preset,
            '-cq', str(quality),
            '-g', str(gop),
            '-tune', 'hq',
            '-spatial-aq', '1',
            '-temporal-aq', '1',
            '-rc-lookahead', '32',
            '-bf', '3',
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-movflags', '+faststart'
        ]
    elif encoder == 'libx265' or encoder == 'libx264':
        return encoder, [
            '-preset', preset,
            '-crf', str(quality),
            '-g', str(gop),
            '-pix_fmt', 'yuv420p',
            '-profile:v', 'main',
            '-movflags', '+faststart'
        ]
    elif encoder == 'hevc_qsv' or encoder == 'h264_qsv':
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

def setup_logger():
    """初始化日志记录器"""
    global logger
    
    if logger is not None:
        return logger
    
    # 检查是否是子进程（通过命令行参数判断，更可靠）
    import sys
    is_child_process = any('--multiprocessing' in arg for arg in sys.argv)
    
    # 另一种判断方式：检查是否有spawn参数
    is_child_process = is_child_process or any('spawn' in arg for arg in sys.argv)
    
    # 另一种判断方式：检查是否有pipe_handle参数
    is_child_process = is_child_process or any('pipe_handle' in arg for arg in sys.argv)
    
    # 另一种判断方式：检查是否有parent_pid参数
    is_child_process = is_child_process or any('parent_pid' in arg for arg in sys.argv)
    
    logger = logging.getLogger('MakeVideo')
    logger.setLevel(logging.INFO)  # 提高日志级别，只记录关键信息
    logger.handlers = []
    
    # 只有主进程创建日志文件，子进程只输出到控制台
    if not is_child_process:
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(LOG_DIR, f'makevideo_{timestamp}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)  # 提高文件日志级别
        logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置控制台输出编码为utf-8，解决中文乱码问题
    if hasattr(console_handler, 'set_encoding'):
        console_handler.set_encoding('utf-8')
    else:
        # 兼容旧版本Python
        import sys
        # 检查sys.stdout和sys.stderr是否为None（在GUI应用中可能为None）
        if sys.stdout and sys.stderr and sys.stdout.encoding != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # 只在主进程中设置file_handler的formatter
    if not is_child_process:
        file_handler.setFormatter(formatter)
    
    console_handler.setFormatter(formatter)
    
    # 只在主进程中添加file_handler
    # file_handler已经在前面添加了
    
    logger.addHandler(console_handler)
    
    # 只在主进程中记录日志文件路径
    if not is_child_process:
        logger.info(f"日志文件: {os.path.abspath(log_file)}")
    
    return logger

def get_logger():
    """获取日志记录器"""
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
        # 记录详细的命令执行信息
        cmd_str = ' '.join(cmd)
        logger.info(f"执行{description}: {cmd_str}")
        
        # 使用shell=False，确保命令行参数能够正确处理
        # 添加超时参数，避免命令执行时间过长
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
