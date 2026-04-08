import os
import random
from utils import VIDEO_DIR, CACHE_DIR, FFMPEG_PATH, get_media_duration, run_ffmpeg_command, DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT, get_logger

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
    
    # ========== 已修复：无损切片，不压缩、不毁画质 ==========
    cmd = [
        FFMPEG_PATH,
        '-ss', str(actual_start),
        '-i', video_path,
        '-t', str(actual_duration),
        '-c:v', 'copy',       # 无损复制
        '-an',                # 移除音频，避免干扰
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
    """获取随机视频，优先选择未使用过的视频"""
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
    target_duration = mp3_duration + 3   # 修复：不需要+60秒，浪费空间
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
        
        # ========== 修复：缓存使用 .mkv 更稳定 ==========
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

def get_video_duration(video_path):
    return get_media_duration(video_path)