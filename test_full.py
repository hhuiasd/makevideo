import os
import sys
import subprocess

# 导入utils模块
from utils import FFMPEG_PATH, FFPROBE_PATH, BASE_DIR, MUSIC_DIR, VIDEO_DIR, OUTPUT_DIR, LOG_DIR

print(f"BASE_DIR: {BASE_DIR}")
print(f"FFMPEG_PATH: {FFMPEG_PATH}")
print(f"FFPROBE_PATH: {FFPROBE_PATH}")
print(f"MUSIC_DIR: {MUSIC_DIR}")
print(f"VIDEO_DIR: {VIDEO_DIR}")
print(f"OUTPUT_DIR: {OUTPUT_DIR}")
print(f"LOG_DIR: {LOG_DIR}")

# 检查ffmpeg是否存在
if os.path.exists(FFMPEG_PATH):
    print("ffmpeg.exe 存在")
else:
    print("ffmpeg.exe 不存在")

# 检查ffprobe是否存在
if os.path.exists(FFPROBE_PATH):
    print("ffprobe.exe 存在")
else:
    print("ffprobe.exe 不存在")

# 尝试运行ffmpeg命令
print("\n尝试运行ffmpeg命令...")
try:
    result = subprocess.run(
        [FFMPEG_PATH, '-version'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=10
    )
    print(f"ffmpeg版本: {result.stdout.splitlines()[0]}")
except Exception as e:
    print(f"运行ffmpeg命令时出错: {str(e)}")

# 检查目录是否存在
print("\n检查目录是否存在...")
directories = [MUSIC_DIR, VIDEO_DIR, OUTPUT_DIR, LOG_DIR]
for directory in directories:
    if os.path.exists(directory):
        print(f"{directory} 存在")
    else:
        print(f"{directory} 不存在")

# 检查MP3文件
print("\n检查MP3文件...")
if os.path.exists(MUSIC_DIR):
    mp3_files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith('.mp3')]
    print(f"找到 {len(mp3_files)} 个MP3文件")
    for mp3_file in mp3_files[:5]:  # 只显示前5个
        print(f"  {mp3_file}")
else:
    print("MUSIC目录不存在，无法检查MP3文件")

# 检查视频文件
print("\n检查视频文件...")
if os.path.exists(VIDEO_DIR):
    video_files = [f for f in os.listdir(VIDEO_DIR) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    print(f"找到 {len(video_files)} 个视频文件")
    for video_file in video_files[:5]:  # 只显示前5个
        print(f"  {video_file}")
else:
    print("VIDEO目录不存在，无法检查视频文件")

print("\n测试完成")
input("按回车键退出...")
