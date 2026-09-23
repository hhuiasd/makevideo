import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import sys
import subprocess
from datetime import datetime, timedelta
import psutil
import time
import configparser

class VideoMixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("视频快速混剪工具 - 1.0     制作：老胡")
        self.root.geometry("950x900")
        self.root.resizable(True, True)
        
        self.process = None
        self.is_running = False
        
        self.create_widgets()
        self.load_default_values()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        info_frame = ttk.LabelFrame(main_frame, text="项目说明", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        project_info = """视频快速混剪工具 - 自动从视频素材中随机切片并合成为视频
功能特点：
• 适用于快速制作批量卡点视频
• 适用于素材批量混剪
• 适用于短剧解说背景内容快速生成
• 功能纯粹，代码开源，处理速度快
• 全流程无损处理，保证画质"""
        
        info_label = ttk.Label(info_frame, text=project_info, justify=tk.LEFT, wraplength=400)
        info_label.grid(row=0, column=0, sticky=tk.W)
        
        flow_frame = ttk.LabelFrame(main_frame, text="简易说明", padding="10")
        flow_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        flow_info = """处理流程：
1. 把视频素材放在video目录下
2. 把音乐素材放在music目录下
3. 选择你需要的编码器和编码预设及质量参数、分辨率（横竖屏）
4. N卡选择nvenc，intel核显选择qsv，CPU选择libx265
5. 根据硬件选择用内存（memory）还是硬盘(disk)当缓存"""
        
        flow_label = ttk.Label(flow_frame, text=flow_info, justify=tk.LEFT, wraplength=400)
        flow_label.grid(row=0, column=0, sticky=tk.W)
        
        encoder_frame = ttk.LabelFrame(main_frame, text="编码参数设置", padding="10")
        encoder_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Label(encoder_frame, text="编码器:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.encoder_var = tk.StringVar()
        self.encoder_combo = ttk.Combobox(encoder_frame, textvariable=self.encoder_var, 
                                          values=["hevc_nvenc", "h264_nvenc", "libx265", "libx264", "hevc_qsv", "h264_qsv"], 
                                          state="readonly", width=15)
        self.encoder_combo.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        self.encoder_combo.bind("<<ComboboxSelected>>", self.on_encoder_change)
        
        ttk.Label(encoder_frame, text="编码预设:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(encoder_frame, textvariable=self.preset_var, 
                                         values=["p1", "p2", "p3", "p4", "p5", "p6", "p7"], 
                                         state="readonly", width=10)
        self.preset_combo.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(encoder_frame, text="质量参数(CQ/CRF):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.quality_var = tk.StringVar()
        self.quality_entry = ttk.Entry(encoder_frame, textvariable=self.quality_var, width=10)
        self.quality_entry.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(encoder_frame, text="(数值越小质量越高，范围18-35)").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2, padx=(5, 0))
        
        ttk.Label(encoder_frame, text="输出分辨率:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.resolution_var = tk.StringVar()
        self.resolution_combo = ttk.Combobox(encoder_frame, textvariable=self.resolution_var, 
                                             values=["1280x720", "1920x1080", "854x480", "640x360", "1080x1920", "720x1280", "1440x2560", "828x1792"], 
                                             state="readonly", width=15)
        self.resolution_combo.grid(row=4, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(encoder_frame, text="GOP大小:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.gop_var = tk.StringVar()
        self.gop_entry = ttk.Entry(encoder_frame, textvariable=self.gop_var, width=10)
        self.gop_entry.grid(row=5, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(encoder_frame, text="缓存类型:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.cache_type_var = tk.StringVar()
        self.cache_type_combo = ttk.Combobox(encoder_frame, textvariable=self.cache_type_var, 
                                             values=["memory", "disk"], 
                                             state="readonly", width=15)
        self.cache_type_combo.grid(row=6, column=1, sticky=tk.W, pady=2, padx=5)
        
        param_frame = ttk.LabelFrame(main_frame, text="切片参数设置", padding="10")
        param_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Label(param_frame, text="跳过视频开头秒数:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.skip_start_var = tk.StringVar()
        self.skip_start_entry = ttk.Entry(param_frame, textvariable=self.skip_start_var, width=10)
        self.skip_start_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(param_frame, text="跳过视频结尾秒数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.skip_end_var = tk.StringVar()
        self.skip_end_entry = ttk.Entry(param_frame, textvariable=self.skip_end_var, width=10)
        self.skip_end_entry.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(param_frame, text="最小切片时长秒数:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.min_slice_var = tk.StringVar()
        self.min_slice_entry = ttk.Entry(param_frame, textvariable=self.min_slice_var, width=10)
        self.min_slice_entry.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(param_frame, text="最大切片时长秒数:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.max_slice_var = tk.StringVar()
        self.max_slice_entry = ttk.Entry(param_frame, textvariable=self.max_slice_var, width=10)
        self.max_slice_entry.grid(row=3, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(param_frame, text="锐化滤镜:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.sharpen_var = tk.BooleanVar()
        self.sharpen_check = ttk.Checkbutton(param_frame, variable=self.sharpen_var, text="启用")
        self.sharpen_check.grid(row=4, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(param_frame, text="锐化参数:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.sharpen_params_var = tk.StringVar()
        self.sharpen_params_entry = ttk.Entry(param_frame, textvariable=self.sharpen_params_var, width=20)
        self.sharpen_params_entry.grid(row=5, column=1, sticky=tk.W, pady=2, padx=5)
        ttk.Label(param_frame, text="(格式: 5:5:0.6)").grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(param_frame, text="转场特效:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.transition_var = tk.BooleanVar()
        self.transition_check = ttk.Checkbutton(param_frame, variable=self.transition_var, text="启用")
        self.transition_check.grid(row=7, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(param_frame, text="转场时长(秒):").grid(row=8, column=0, sticky=tk.W, pady=2)
        self.transition_duration_var = tk.StringVar()
        self.transition_duration_entry = ttk.Entry(param_frame, textvariable=self.transition_duration_var, width=10)
        self.transition_duration_entry.grid(row=8, column=1, sticky=tk.W, pady=2, padx=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="开始处理", command=self.start_processing)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止处理", command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        self.clean_button = ttk.Button(button_frame, text="清理缓存", command=self.clean_cache)
        self.clean_button.grid(row=0, column=2, padx=5)
        
        self.open_output_button = ttk.Button(button_frame, text="打开输出目录", command=self.open_output_dir)
        self.open_output_button.grid(row=0, column=3, padx=5)
        
        self.open_log_button = ttk.Button(button_frame, text="打开日志", command=self.open_log)
        self.open_log_button.grid(row=0, column=4, padx=5)
        
        self.save_default_button = ttk.Button(button_frame, text="保存为默认配置", command=self.save_default_config)
        self.save_default_button.grid(row=0, column=5, padx=5)
        
        self.contact_button = ttk.Button(button_frame, text="联系作者", command=self.open_contact)
        self.contact_button.grid(row=0, column=6, padx=5)
        
        self.exit_button = ttk.Button(button_frame, text="关闭退出", command=self.root.quit)
        self.exit_button.grid(row=0, column=7, padx=5)
        
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 状态标签
        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=5)
        
        # 横排显示状态信息和资源占用
        status_grid = ttk.Frame(progress_frame)
        status_grid.grid(row=1, column=0, columnspan=6, sticky=(tk.W, tk.E))
        
        # 耗时
        ttk.Label(status_grid, text="耗时:", width=8).grid(row=0, column=0, sticky=tk.W, padx=5)
        self.time_elapsed_var = tk.StringVar(value="00:00:00")
        ttk.Label(status_grid, textvariable=self.time_elapsed_var, width=12).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # CPU占用
        ttk.Label(status_grid, text="CPU:", width=8).grid(row=0, column=2, sticky=tk.W, padx=5)
        self.cpu_var = tk.StringVar(value="0%")
        ttk.Label(status_grid, textvariable=self.cpu_var, width=10).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # 内存占用
        ttk.Label(status_grid, text="内存:", width=8).grid(row=0, column=4, sticky=tk.W, padx=5)
        self.memory_var = tk.StringVar(value="0%")
        ttk.Label(status_grid, textvariable=self.memory_var, width=10).grid(row=0, column=5, sticky=tk.W, padx=5)
        
        # 配置列宽
        for i in range(6):
            status_grid.columnconfigure(i, weight=0)
        
        # 启动资源监控线程
        self.monitoring = False
        self.resource_thread = None
        
        log_frame = ttk.LabelFrame(main_frame, text="日志输出", padding="10")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        main_frame.rowconfigure(4, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=12, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def load_default_values(self):
        # 从config.ini文件读取默认配置
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')
        
        # 切片参数
        self.skip_start_var.set(str(config.get('Default', 'skip_start', fallback=2)))
        self.skip_end_var.set(str(config.get('Default', 'skip_end', fallback=0)))
        self.min_slice_var.set(str(config.get('Default', 'min_slice', fallback=2)))
        self.max_slice_var.set(str(config.get('Default', 'max_slice', fallback=4)))
        
        # 编码参数
        self.encoder_var.set(config.get('Default', 'encoder', fallback='hevc_nvenc'))
        self.preset_var.set(config.get('Default', 'preset', fallback='p7'))
        self.quality_var.set(str(config.get('Default', 'quality', fallback=28)))
        self.resolution_var.set(config.get('Default', 'resolution', fallback='1280x720'))
        self.gop_var.set(str(config.get('Default', 'gop', fallback=120)))
        
        # 锐化参数
        self.sharpen_var.set(config.getboolean('Default', 'sharpen', fallback=False))
        self.sharpen_params_var.set(config.get('Default', 'sharpen_params', fallback='5:5:0.6'))
        
        # 转场参数
        self.transition_var.set(config.getboolean('Default', 'transition', fallback=True))
        self.transition_duration_var.set(str(config.get('Default', 'transition_duration', fallback=0.7)))
        
        # 缓存类型
        self.cache_type_var.set(config.get('Default', 'cache_type', fallback='memory'))
        
        # 触发编码器变更事件，更新预设选项
        self.on_encoder_change(None)
        
    def on_encoder_change(self, event):
        encoder = self.encoder_var.get()
        if encoder == "hevc_nvenc" or encoder == "h264_nvenc":
            self.preset_combo['values'] = ["p1", "p2", "p3", "p4", "p5", "p6", "p7"]
            self.preset_var.set("p7")
        elif encoder == "libx265" or encoder == "libx264":
            self.preset_combo['values'] = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
            self.preset_var.set("slow")
        elif encoder == "hevc_qsv" or encoder == "h264_qsv":
            self.preset_combo['values'] = ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
            self.preset_var.set("slow")
        
    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        # 确保消息能够正确显示中文
        try:
            if isinstance(message, bytes):
                message = message.decode('utf-8', errors='replace')
            elif not isinstance(message, str):
                message = str(message)
        except Exception:
            pass
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def update_progress(self, value, text=""):
        if text:
            self.progress_label.config(text=text)
        
    def start_processing(self):
        try:
            skip_start = float(self.skip_start_var.get())
            skip_end = float(self.skip_end_var.get())
            min_slice = float(self.min_slice_var.get())
            max_slice = float(self.max_slice_var.get())
            quality = int(self.quality_var.get())
            gop = int(self.gop_var.get())
            
            if min_slice > max_slice:
                messagebox.showerror("错误", "最小切片时长不能大于最大切片时长")
                return
            
            if quality < 18 or quality > 35:
                messagebox.showerror("错误", "质量参数应在18-35之间")
                return
                
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字参数")
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clean_button.config(state=tk.DISABLED)
        self.exit_button.config(state=tk.DISABLED)
        
        # 开始资源监控
        self.monitoring = True
        self.resource_thread = threading.Thread(target=self.monitor_resources)
        self.resource_thread.daemon = True
        self.resource_thread.start()
        
        encoder = self.encoder_var.get()
        preset = self.preset_var.get()
        resolution = self.resolution_var.get()
        sharpen_enabled = self.sharpen_var.get()
        sharpen_params = self.sharpen_params_var.get()
        transition_enabled = self.transition_var.get()
        transition_duration = self.transition_duration_var.get()
        
        # 获取缓存类型
        cache_type = self.cache_type_var.get()
        
        self.log_message(f"编码器: {encoder}, 预设: {preset}, 质量: {quality}, 分辨率: {resolution}, GOP: {gop}")
        self.log_message(f"锐化滤镜: {'启用' if sharpen_enabled else '禁用'}{' (' + sharpen_params + ')' if sharpen_enabled else ''}")
        self.log_message(f"转场特效: {'启用' if transition_enabled else '禁用'}{' (' + transition_duration + '秒)' if transition_enabled else ''}")
        self.log_message(f"缓存类型: {cache_type}")
        self.log_message("开始处理...")
        self.update_progress(0, "正在处理...")
        
        thread = threading.Thread(target=self.run_processing, 
                                 args=(skip_start, skip_end, min_slice, max_slice, 
                                       encoder, preset, quality, resolution, gop, 
                                       sharpen_enabled, sharpen_params, 
                                       transition_enabled, transition_duration, cache_type))
        thread.daemon = True
        thread.start()
        
    def run_processing(self, skip_start, skip_end, min_slice, max_slice, 
                      encoder, preset, quality, resolution, gop, 
                      sharpen_enabled, sharpen_params, 
                      transition_enabled, transition_duration, cache_type):
        try:
            # 构建命令，调用makevideo.exe
            # 使用当前工作目录，确保在打包后能找到makevideo.exe
            # 检查是否在运行 Python 脚本（而不是打包后的可执行文件）
            if getattr(sys, 'frozen', False):
                # 运行的是打包后的可执行文件，使用 makevideo.exe
                exe_path = os.path.join(os.getcwd(), "makevideo.exe")
                cmd = [
                    exe_path,
                    str(skip_start), str(skip_end), str(min_slice), str(max_slice),
                    "--encoder", encoder,
                    "--preset", preset,
                    "--quality", str(quality),
                    "--resolution", resolution,
                    "--gop", str(gop),
                    "--sharpen", str(sharpen_enabled),
                    "--sharpen-params", sharpen_params,
                    "--transition", str(transition_enabled),
                    "--transition-duration", transition_duration,
                    "--cache-type", cache_type
                ]
            else:
                # 运行的是 Python 脚本，使用 Python 解释器运行 main.py
                python_exe = sys.executable
                main_py = os.path.join(os.getcwd(), "main.py")
                cmd = [
                    python_exe,
                    main_py,
                    str(skip_start), str(skip_end), str(min_slice), str(max_slice),
                    "--encoder", encoder,
                    "--preset", preset,
                    "--quality", str(quality),
                    "--resolution", resolution,
                    "--gop", str(gop),
                    "--sharpen", str(sharpen_enabled),
                    "--sharpen-params", sharpen_params,
                    "--transition", str(transition_enabled),
                    "--transition-duration", transition_duration,
                    "--cache-type", cache_type
                ]
            
            # 打印构建的命令，用于调试
            self.log_message(f"构建的命令: {' '.join(cmd)}")
            
            start_time = datetime.now()
            
            # 设置当前工作目录为release目录
            cwd = os.getcwd()
            self.log_message(f"当前工作目录: {cwd}")
            
            # 检查必要的目录是否存在
            required_dirs = ['music', 'video', 'output']
            for dir_name in required_dirs:
                dir_path = os.path.join(cwd, dir_name)
                if not os.path.exists(dir_path):
                    self.log_message(f"警告: {dir_name} 目录不存在，正在创建...")
                    os.makedirs(dir_path, exist_ok=True)
                    self.log_message(f"创建 {dir_name} 目录成功")
            
            # 检查music目录是否有MP3文件
            music_dir = os.path.join(cwd, 'music')
            mp3_files = [f for f in os.listdir(music_dir) if f.lower().endswith('.mp3')]
            if not mp3_files:
                self.log_message("警告: music目录中未找到MP3文件")
                self.log_message("请在music目录中添加MP3文件后重试")
                self.update_progress(0, "缺少MP3文件")
                messagebox.showerror("错误", "music目录中未找到MP3文件，请添加后重试")
                return
            
            # 检查video目录是否有视频文件
            video_dir = os.path.join(cwd, 'video')
            video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']
            video_files = [f for f in os.listdir(video_dir) if any(f.lower().endswith(ext) for ext in video_extensions)]
            if not video_files:
                self.log_message("警告: video目录中未找到视频文件")
                self.log_message("请在video目录中添加视频文件后重试")
                self.update_progress(0, "缺少视频文件")
                messagebox.showerror("错误", "video目录中未找到视频文件，请添加后重试")
                return
            
            # 开始处理
            self.log_message(f"找到 {len(mp3_files)} 个MP3文件和 {len(video_files)} 个视频文件")
            self.log_message("开始处理...")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=cwd
            )
            
            # 读取输出
            error_occurred = False
            for line in iter(self.process.stdout.readline, ''):
                if not self.is_running:
                    break
                    
                line = line.strip()
                if line:
                    try:
                        line = line.encode('utf-8').decode('utf-8')
                    except:
                        pass
                    self.log_message(line)
                    
                    # 检查是否有错误信息
                    if 'ERROR' in line or 'error' in line.lower():
                        error_occurred = True
                    
                    elapsed = datetime.now() - start_time
                    self.time_elapsed_var.set(str(elapsed).split('.')[0])
            
            self.process.wait()
            
            # 根据返回码和错误信息判断处理结果
            if self.process.returncode == 0 and not error_occurred:
                self.log_message("处理完成！")
                self.update_progress(100, "处理完成")
                messagebox.showinfo("完成", "视频处理完成！")
            else:
                self.log_message(f"处理失败，退出码: {self.process.returncode}")
                self.update_progress(0, "处理失败")
                messagebox.showerror("错误", "处理失败，请查看日志")
                
        except Exception as e:
            self.log_message(f"处理出错: {str(e)}")
            self.update_progress(0, "处理出错")
            messagebox.showerror("错误", f"处理出错: {str(e)}")
            
        finally:
            self.is_running = False
            self.monitoring = False
            self.process = None
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.clean_button.config(state=tk.NORMAL)
            self.exit_button.config(state=tk.NORMAL)
            
    def stop_processing(self):
        if self.process and self.is_running:
            self.is_running = False
            self.monitoring = False
            self.process.terminate()
            self.log_message("正在停止处理...")
            self.update_progress(0, "已停止")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.clean_button.config(state=tk.NORMAL)
            self.exit_button.config(state=tk.NORMAL)
    
    def monitor_resources(self):
        while self.monitoring:
            try:
                # 获取CPU占用
                cpu_percent = psutil.cpu_percent(interval=1)
                self.cpu_var.set(f"{cpu_percent:.1f}%")
                
                # 获取内存占用
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.memory_var.set(f"{memory_percent:.1f}%")
                
                # 短暂休眠
                time.sleep(1)
            except Exception:
                pass
            
    def clean_cache(self):
        try:
            # 使用与 utils.py 中相同的逻辑来确定缓存目录
            import tempfile
            
            # 首先检查内存缓存目录
            memory_cache_dir = os.path.join(r'\\.\pipe', 'makevideo_cache')
            if os.path.exists(memory_cache_dir):
                import shutil
                shutil.rmtree(memory_cache_dir)
                self.log_message("内存缓存清理完成")
                messagebox.showinfo("完成", "内存缓存清理完成！")
                return
            
            # 然后检查磁盘缓存目录
            disk_cache_dir = os.path.join(os.getcwd(), "cache")
            if os.path.exists(disk_cache_dir):
                import shutil
                shutil.rmtree(disk_cache_dir)
                self.log_message("磁盘缓存清理完成")
                messagebox.showinfo("完成", "磁盘缓存清理完成！")
                return
            
            # 最后检查临时目录中的缓存
            temp_cache_dir = os.path.join(tempfile.gettempdir(), 'makevideo_cache')
            if os.path.exists(temp_cache_dir):
                import shutil
                shutil.rmtree(temp_cache_dir)
                self.log_message("临时缓存清理完成")
                messagebox.showinfo("完成", "临时缓存清理完成！")
                return
            
            # 如果所有缓存目录都不存在
            self.log_message("缓存目录不存在")
            messagebox.showinfo("提示", "缓存目录不存在")
        except Exception as e:
            self.log_message(f"清理缓存失败: {str(e)}")
            messagebox.showerror("错误", f"清理缓存失败: {str(e)}")
            
    def open_output_dir(self):
        # 使用当前工作目录来查找 output 目录
        output_dir = os.path.join(os.getcwd(), "output")
        if os.path.exists(output_dir):
            os.startfile(output_dir)
        else:
            messagebox.showinfo("提示", "输出目录不存在")
    
    def open_log(self):
        # 使用当前工作目录来查找 log 目录
        log_dir = os.path.join(os.getcwd(), "log")
        if not os.path.exists(log_dir):
            messagebox.showinfo("提示", "日志目录不存在")
            return
        
        # 获取所有日志文件
        log_files = []
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                log_files.append((os.path.getmtime(file_path), file_path))
        
        if not log_files:
            messagebox.showinfo("提示", "没有找到日志文件")
            return
        
        # 按修改时间排序，取最新的日志文件
        log_files.sort(reverse=True)
        latest_log = log_files[0][1]
        
        try:
            os.startfile(latest_log)
            self.log_message(f"已打开最新日志文件: {os.path.basename(latest_log)}")
        except Exception as e:
            self.log_message(f"打开日志文件失败: {str(e)}")
            messagebox.showerror("错误", f"打开日志文件失败: {str(e)}")
    
    def open_contact(self):
        import webbrowser
        webbrowser.open('https://www.j6s.net/addlaohu/')

    def save_default_config(self):
        try:
            # 获取当前设置
            skip_start = float(self.skip_start_var.get())
            skip_end = float(self.skip_end_var.get())
            min_slice = float(self.min_slice_var.get())
            max_slice = float(self.max_slice_var.get())
            quality = int(self.quality_var.get())
            gop = int(self.gop_var.get())
            
            if min_slice > max_slice:
                messagebox.showerror("错误", "最小切片时长不能大于最大切片时长")
                return
            
            if quality < 18 or quality > 35:
                messagebox.showerror("错误", "质量参数应在18-35之间")
                return
            
            # 其他参数
            encoder = self.encoder_var.get()
            preset = self.preset_var.get()
            resolution = self.resolution_var.get()
            sharpen_enabled = self.sharpen_var.get()
            sharpen_params = self.sharpen_params_var.get()
            transition_enabled = self.transition_var.get()
            transition_duration = float(self.transition_duration_var.get())
            cache_type = self.cache_type_var.get()
            
            # 保存到config.ini文件
            config = configparser.ConfigParser()
            config['Default'] = {
                'skip_start': str(skip_start),
                'skip_end': str(skip_end),
                'min_slice': str(min_slice),
                'max_slice': str(max_slice),
                'encoder': encoder,
                'preset': preset,
                'quality': str(quality),
                'resolution': resolution,
                'gop': str(gop),
                'sharpen': str(sharpen_enabled),
                'sharpen_params': sharpen_params,
                'transition': str(transition_enabled),
                'transition_duration': str(transition_duration),
                'cache_type': cache_type
            }
            
            with open('config.ini', 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            
            self.log_message("默认配置保存成功！")
            messagebox.showinfo("成功", "默认配置保存成功！")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字参数")
        except Exception as e:
            self.log_message(f"保存默认配置失败: {str(e)}")
            messagebox.showerror("错误", f"保存默认配置失败: {str(e)}")

def main():
    root = tk.Tk()
    app = VideoMixGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
