import os
import random
from utils import MUSIC_DIR, get_media_duration, get_logger

def get_all_mp3_files():
    mp3_files = []
    if not os.path.exists(MUSIC_DIR):
        return mp3_files
    
    for filename in os.listdir(MUSIC_DIR):
        if filename.lower().endswith('.mp3'):
            mp3_files.append(filename)
    
    return mp3_files

def get_mp3_durations():
    mp3_info = {}
    mp3_files = get_all_mp3_files()
    
    print(f"找到 {len(mp3_files)} 个MP3文件")
    
    for mp3_file in mp3_files:
        mp3_path = os.path.join(MUSIC_DIR, mp3_file)
        duration = get_media_duration(mp3_path)
        
        if duration > 0:
            mp3_info[mp3_file] = duration
            print(f"  {mp3_file}: {duration:.2f}秒")
        else:
            print(f"  {mp3_file}: 获取时长失败")
    
    return mp3_info

def get_random_mp3():
    mp3_files = get_all_mp3_files()
    if not mp3_files:
        return None, 0
    
    mp3_file = random.choice(mp3_files)
    mp3_path = os.path.join(MUSIC_DIR, mp3_file)
    duration = get_media_duration(mp3_path)
    
    return mp3_file, duration

def get_mp3_duration(mp3_file):
    mp3_path = os.path.join(MUSIC_DIR, mp3_file)
    return get_media_duration(mp3_path)
