import os
import sys
import traceback
import multiprocessing
import argparse
import configparser
from utils import ensure_directories, MUSIC_DIR, VIDEO_DIR, CACHE_DIR, OUTPUT_DIR, LOG_DIR, FFMPEG_PATH, FFPROBE_PATH, detect_gpu_acceleration, get_logger, setup_logger, set_encoder_config, encoder_config, set_cache_type
import audio_processor
import video_processor
import merger
import finalizer
import cleanup

# 读取配置文件
def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    
    # 切片参数
    skip_start = float(config.get('Default', 'skip_start', fallback=2))
    skip_end = float(config.get('Default', 'skip_end', fallback=0))
    min_slice = float(config.get('Default', 'min_slice', fallback=2))
    max_slice = float(config.get('Default', 'max_slice', fallback=4))
    
    # 编码参数
    encoder = config.get('Default', 'encoder', fallback='hevc_nvenc')
    preset = config.get('Default', 'preset', fallback='p7')
    quality = int(config.get('Default', 'quality', fallback=28))
    resolution = config.get('Default', 'resolution', fallback='1280x720')
    gop = int(config.get('Default', 'gop', fallback=120))
    
    # 锐化参数
    sharpen = config.getboolean('Default', 'sharpen', fallback=False)
    sharpen_params = config.get('Default', 'sharpen_params', fallback='5:5:0.6')
    
    # 转场参数
    transition = config.getboolean('Default', 'transition', fallback=True)
    transition_duration = float(config.get('Default', 'transition_duration', fallback=0.7))
    
    return (skip_start, skip_end, min_slice, max_slice, 
            encoder, preset, quality, resolution, gop, 
            sharpen, sharpen_params, transition, transition_duration)

def process_single_mp3(mp3_file, skip_start, skip_end, min_slice, max_slice, 
                      encoder, preset, quality, resolution, gop, 
                      sharpen=True, sharpen_params='5:5:0.8', 
                      transition=True, transition_duration=0.6):
    """处理单个MP3文件的函数"""
    logger = get_logger()
    try:
        logger.info(f"处理音乐: {mp3_file}")
        logger.info("-" * 60)
        
        mp3_duration = audio_processor.get_mp3_duration(mp3_file)
        
        if mp3_duration <= 0:
            logger.warning(f"跳过无效的MP3文件: {mp3_file}")
            return False, mp3_file
        
        logger.info(f"MP3时长: {mp3_duration:.2f}秒")
        
        logger.info("步骤1: 为音乐创建视频切片...")
        slices = video_processor.create_random_slices(
            mp3_file, mp3_duration, 
            skip_start=skip_start, 
            skip_end=skip_end, 
            min_slice=min_slice, 
            max_slice=max_slice
        )
        
        if not slices:
            logger.error(f"无法为 {mp3_file} 创建足够的切片")
            cleanup.cleanup_specific_files(slices)
            return False, mp3_file
        
        temp_output = os.path.join(CACHE_DIR, f"temp_{os.path.splitext(mp3_file)[0]}_{os.getpid()}.mp4")
        
        logger.info("步骤2: 合并视频并添加转场...")
        if not merger.merge_videos_with_transitions(slices, temp_output, 
                                                  transition=transition, 
                                                  transition_duration=transition_duration,
                                                  resolution=resolution):
            logger.error("合并视频失败")
            cleanup.cleanup_specific_files(slices)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False, mp3_file
        
        output_name = f"{os.path.splitext(mp3_file)[0]}.mp4"
        output_path = os.path.join('output', output_name)
        
        logger.info("步骤3: 最终处理（添加背景音乐并编码）...")
        if finalizer.finalize_video(temp_output, mp3_file, output_path, 
                                   encoder=encoder, preset=preset, quality=quality, 
                                   resolution=resolution, gop=gop, 
                                   sharpen=sharpen, sharpen_params=sharpen_params):
            logger.info(f"成功生成: {output_path}")
            cleanup.cleanup_specific_files(slices)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return True, mp3_file
        else:
            logger.error(f"最终处理失败: {mp3_file}")
            cleanup.cleanup_specific_files(slices)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False, mp3_file
            
    except Exception as e:
        error_msg = f"处理 {mp3_file} 时出错: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, mp3_file

def process_video_mixing(skip_start=1, skip_end=0, min_slice=2, max_slice=5, 
                       sharpen=True, sharpen_params='5:5:0.6', 
                       transition=True, transition_duration=0.6):
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
        
        mp3_files = audio_processor.get_all_mp3_files()
        if not mp3_files:
            error_msg = "错误: 未找到MP3文件，请在music目录中添加MP3文件"
            logger.error(error_msg)
            return False
        
        video_files = video_processor.get_all_video_files()
        if not video_files:
            error_msg = "错误: 未找到视频文件，请在video目录中添加视频文件"
            logger.error(error_msg)
            return False
        
        logger.info(f"找到 {len(mp3_files)} 个MP3文件和 {len(video_files)} 个视频文件")
        logger.info(f"处理参数: 跳过开头={skip_start}秒, 跳过结尾={skip_end}秒, 切片时长={min_slice}-{max_slice}秒")
        logger.info("")
        
        pool_size = 2
        logger.info(f"使用 {pool_size} 个进程并行处理")
        logger.info("")
        
        # 获取当前编码配置
        encoder = encoder_config['encoder']
        preset = encoder_config['preset']
        quality = encoder_config['quality']
        resolution = encoder_config['resolution']
        gop = encoder_config['gop']
        
        tasks = [(mp3_file, skip_start, skip_end, min_slice, max_slice, 
                 encoder, preset, quality, resolution, gop, 
                 sharpen, sharpen_params, transition, transition_duration) for mp3_file in mp3_files]
        
        # 使用spawn上下文创建进程池，避免每个子进程都启动一个新的makevideo.exe
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(processes=pool_size) as pool:
            results = pool.starmap(process_single_mp3, tasks)
        
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
        
        cleanup.report_completion(successful_outputs, mp3_files)
        
        logger.info("\n清理缓存...")
        cleanup.cleanup_cache()
        
        logger.info("\n所有处理完成！")
        return True
        
    except Exception as e:
        error_msg = f"\n程序运行出错: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        cleanup.report_error(str(e))
        return False

def main(args=None):
    setup_logger()
    logger = get_logger()
    
    # 检查是否是子进程，如果是子进程，直接返回，不执行主逻辑
    import sys
    is_child_process = any('--multiprocessing' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('spawn' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('pipe_handle' in arg for arg in sys.argv)
    is_child_process = is_child_process or any('parent_pid' in arg for arg in sys.argv)
    
    if is_child_process:
        # 子进程只需要导入模块，不需要执行主逻辑
        return
    
    try:
        # 加载默认配置
        default_config = load_config()
        (default_skip_start, default_skip_end, default_min_slice, default_max_slice, 
         default_encoder, default_preset, default_quality, default_resolution, default_gop, 
         default_sharpen, default_sharpen_params, default_transition, default_transition_duration) = default_config
        
        parser = argparse.ArgumentParser(description='视频快速混剪工具')
        parser.add_argument('skip_start', nargs='?', type=float, default=default_skip_start, help='跳过视频开头秒数')
        parser.add_argument('skip_end', nargs='?', type=float, default=default_skip_end, help='跳过视频结尾秒数')
        parser.add_argument('min_slice', nargs='?', type=float, default=default_min_slice, help='最小切片时长秒数')
        parser.add_argument('max_slice', nargs='?', type=float, default=default_max_slice, help='最大切片时长秒数')
        parser.add_argument('--encoder', type=str, default=default_encoder, 
                           choices=['hevc_nvenc', 'libx265', 'hevc_qsv'],
                           help='视频编码器')
        parser.add_argument('--preset', type=str, default=default_preset, help='编码预设')
        parser.add_argument('--quality', type=int, default=default_quality, help='质量参数(CQ/CRF)')
        parser.add_argument('--resolution', type=str, default=default_resolution, help='输出分辨率')
        parser.add_argument('--gop', type=int, default=default_gop, help='GOP大小')
        parser.add_argument('--sharpen', type=lambda x: x.lower() == 'true', default=default_sharpen, help='是否启用锐化滤镜')
        parser.add_argument('--sharpen-params', type=str, default=default_sharpen_params, help='锐化滤镜参数')
        parser.add_argument('--transition', type=lambda x: x.lower() == 'true', default=default_transition, help='是否启用转场特效')
        parser.add_argument('--transition-duration', type=float, default=default_transition_duration, help='转场时长(秒)')
        parser.add_argument('--cache-type', type=str, choices=['memory', 'disk'], default='memory', help='缓存类型')
        
        # 保存原始的sys.argv，用于setup_logger函数判断是否是子进程
        # 注意：不要修改sys.argv，因为setup_logger会使用它
        
        if args:
            # 过滤掉可能的额外参数，比如 parent_pid=16188、pipe_handle=536 或 --multiprocessing-fork
            filtered_args = []
            for arg in args:
                # 忽略包含 = 的参数（通常是额外的进程间通信参数）
                # 忽略以 --multiprocessing 开头的参数（multiprocessing 模块传递的参数）
                if '=' not in arg and not arg.startswith('--multiprocessing'):
                    filtered_args.append(arg)
            args = parser.parse_args(filtered_args)
        else:
            # 过滤掉可能的额外参数，比如 parent_pid=16188、pipe_handle=536 或 --multiprocessing-fork
            filtered_args = []
            for arg in sys.argv[1:]:
                # 忽略包含 = 的参数（通常是额外的进程间通信参数）
                # 忽略以 --multiprocessing 开头的参数（multiprocessing 模块传递的参数）
                if '=' not in arg and not arg.startswith('--multiprocessing'):
                    filtered_args.append(arg)
            args = parser.parse_args(filtered_args)
        
        set_encoder_config(args.encoder, args.preset, args.quality, args.resolution, args.gop)
        set_cache_type(args.cache_type)
        
        logger.info(f"编码配置: 编码器={args.encoder}, 预设={args.preset}, 质量={args.quality}, 分辨率={args.resolution}, GOP={args.gop}")
        logger.info(f"锐化配置: 启用={args.sharpen}, 参数={args.sharpen_params}")
        logger.info(f"转场配置: 启用={args.transition}, 时长={args.transition_duration}秒")
        logger.info(f"切片参数: 跳过开头={args.skip_start}秒, 跳过结尾={args.skip_end}秒, 切片时长={args.min_slice}-{args.max_slice}秒")
        
        process_video_mixing(args.skip_start, args.skip_end, args.min_slice, args.max_slice, 
                           args.sharpen, args.sharpen_params, 
                           args.transition, args.transition_duration)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        cleanup.cleanup_all()
        sys.exit(0)
    except Exception as e:
        error_msg = f"程序运行出错: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        cleanup.cleanup_all()
        sys.exit(1)

if __name__ == "__main__":
    main()
