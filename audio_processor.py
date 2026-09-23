import os
from utils import MUSIC_DIR, get_media_duration

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
