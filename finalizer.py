import os
from utils import MUSIC_DIR, FFMPEG_PATH, run_ffmpeg_command, get_media_duration, get_video_encoder, get_logger, encoder_config

def add_background_music(video_path, mp3_file, output_path):
    mp3_path = os.path.join(MUSIC_DIR, mp3_file)
    
    if not os.path.exists(mp3_path):
        print(f"MP3文件不存在: {mp3_path}")
        return False
    
    mp3_duration = get_media_duration(mp3_path)
    
    if mp3_duration <= 0:
        print(f"无法获取MP3时长: {mp3_file}")
        return False
    
    encoder, encoder_params = get_video_encoder()
    
    cmd = [
        FFMPEG_PATH,
        '-i', video_path,
        '-i', mp3_path,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', encoder,
        *encoder_params,
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-y',
        output_path
    ]
    
    success = run_ffmpeg_command(cmd, "添加背景音乐")
    
    return success

def trim_to_audio_duration(video_path, mp3_file, output_path):
    mp3_path = os.path.join(MUSIC_DIR, mp3_file)
    
    if not os.path.exists(mp3_path):
        print(f"MP3文件不存在: {mp3_path}")
        return False
    
    mp3_duration = get_media_duration(mp3_path)
    
    if mp3_duration <= 0:
        print(f"无法获取MP3时长: {mp3_file}")
        return False
    
    encoder, encoder_params = get_video_encoder()
    
    cmd = [
        FFMPEG_PATH,
        '-i', video_path,
        '-i', mp3_path,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', encoder,
        *encoder_params,
        '-c:a', 'aac',
        '-b:a', '128k',
        '-t', str(mp3_duration),
        '-y',
        output_path
    ]
    
    success = run_ffmpeg_command(cmd, f"裁剪到MP3时长({mp3_duration:.2f}秒)")
    
    return success

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
    
    # 如果提供了编码参数，使用它们
    if encoder and preset and quality and gop:
        from utils import set_encoder_config
        # 临时设置编码配置
        original_config = encoder_config.copy()
        set_encoder_config(encoder, preset, quality, resolution, gop)
        
        # 获取编码器参数
        encoder, encoder_params = get_video_encoder()
        
        # 恢复原始配置
        set_encoder_config(
            original_config['encoder'], 
            original_config['preset'], 
            original_config['quality'], 
            original_config['resolution'], 
            original_config['gop']
        )
    else:
        # 使用默认配置
        encoder, encoder_params = get_video_encoder()
    
    fade_start = max(0, mp3_duration - 2)
    
    cmd = [
        FFMPEG_PATH,
        '-i', video_path,
        '-i', mp3_path,
        '-map', '0:v',
        '-map', '1:a',
    ]
    
    # 添加锐化滤镜（如果启用）
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
