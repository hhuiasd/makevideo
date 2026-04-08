import os
import sys
import subprocess

# 导入utils模块
from utils import FFMPEG_PATH, FFPROBE_PATH, BASE_DIR

print(f"BASE_DIR: {BASE_DIR}")
print(f"FFMPEG_PATH: {FFMPEG_PATH}")
print(f"FFPROBE_PATH: {FFPROBE_PATH}")

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

print("\n测试完成")
input("按回车键退出...")
