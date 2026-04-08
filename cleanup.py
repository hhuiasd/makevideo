import os
import shutil
from utils import CACHE_DIR, OUTPUT_DIR, get_logger

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

def get_output_files():
    if not os.path.exists(OUTPUT_DIR):
        return []
    
    output_files = []
    for filename in os.listdir(OUTPUT_DIR):
        if filename.lower().endswith('.mp4'):
            output_files.append(filename)
    
    return output_files

def report_completion(output_files, mp3_files):
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

def report_error(error_message):
    print("\n" + "="*50)
    print("错误报告")
    print("="*50)
    print(f"\n错误信息: {error_message}")
    print("="*50 + "\n")

def report_progress(step, total_steps, message):
    progress = (step / total_steps) * 100
    bar_length = 40
    filled_length = int(bar_length * step / total_steps)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f"\r[{bar}] {progress:.1f}% - {message}", end='', flush=True)
    
    if step == total_steps:
        print()