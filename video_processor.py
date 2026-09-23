import os
import random
from utils import VIDEO_DIR, CACHE_DIR, FFMPEG_PATH, get_media_duration, run_ffmpeg_command, get_logger

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


class VideoPool:
    """视频素材池，确保选取时尽量不重复、不连续选同一视频、时间区间不重叠"""

    def __init__(self, video_files):
        self.video_files = video_files
        self.video_usage_count = {}
        # 记录每个视频已使用的起始时间区间，避免重叠
        self.video_used_ranges = {}  # {filename: [(start, end), ...]}
        # 洗牌队列：每轮把所有视频打乱顺序依次取，用完再洗
        self._queue = []
        self._queue_index = 0
        self._last_video = None
        self._refill_queue()

    def _refill_queue(self):
        """重新洗牌填充队列，排除上一个使用的视频放在队首以避免连续重复"""
        self._queue = list(self.video_files)
        random.shuffle(self._queue)
        # 防止与上一轮最后一个视频连续重复
        if self._last_video and len(self._queue) > 1 and self._queue[0] == self._last_video:
            # 找一个不同的位置交换
            for i in range(1, len(self._queue)):
                if self._queue[i] != self._last_video:
                    self._queue[0], self._queue[i] = self._queue[i], self._queue[0]
                    break
        self._queue_index = 0

    def pick_next(self):
        """从队列中取下一个视频，自动跳过连续重复，用完自动洗牌"""
        if not self._queue:
            return None

        # 尝试从队列中取一个不同于上一个的视频
        attempts = 0
        while self._queue_index < len(self._queue):
            candidate = self._queue[self._queue_index]
            self._queue_index += 1
            # 允许连续选取同一视频仅在素材极少时
            if candidate != self._last_video or len(self.video_files) <= 2:
                self._last_video = candidate
                self.video_usage_count[candidate] = self.video_usage_count.get(candidate, 0) + 1
                return candidate
            attempts += 1

        # 队列用完，重新洗牌
        self._refill_queue()
        if self._queue_index < len(self._queue):
            candidate = self._queue[self._queue_index]
            self._queue_index += 1
            self._last_video = candidate
            self.video_usage_count[candidate] = self.video_usage_count.get(candidate, 0) + 1
            return candidate

        return None

    def add_used_range(self, video_file, start, end):
        """记录已使用的时间区间"""
        if video_file not in self.video_used_ranges:
            self.video_used_ranges[video_file] = []
        self.video_used_ranges[video_file].append((start, end))

    def pick_start_time(self, video_file, min_start, max_start, slice_duration):
        """选取不与已用区间重叠的起始时间，最多尝试20次，找不到则退化为随机"""
        used_ranges = self.video_used_ranges.get(video_file, [])

        for _ in range(20):
            start = random.uniform(min_start, max_start)
            end = start + slice_duration
            # 检查是否与已有区间重叠
            overlap = False
            for (us, ue) in used_ranges:
                if start < ue and end > us:
                    overlap = True
                    break
            if not overlap:
                return start

        # 退化为随机选取
        return random.uniform(min_start, max_start)


def create_random_slices(mp3_name, mp3_duration, skip_start=1, skip_end=0, min_slice=3, max_slice=5):
    logger = get_logger()
    video_files = get_all_video_files()

    if not video_files:
        logger.error("未找到视频文件")
        return []

    logger.info(f"开始为 {mp3_name} 创建切片，可用素材 {len(video_files)} 个")

    total_duration = 0
    slices = []
    pool = VideoPool(video_files)
    max_attempts = 1000
    attempts = 0
    target_duration = mp3_duration + 3

    while total_duration < target_duration and attempts < max_attempts:
        attempts += 1

        video_file = pool.pick_next()
        if video_file is None:
            break

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
        # 使用去重逻辑选取起始时间
        actual_start = pool.pick_start_time(video_file, skip_start, max_start_time, slice_duration)

        # ========== 修复：缓存使用 .mkv 更稳定 ==========
        slice_name = f"{os.path.splitext(mp3_name)[0]}_{len(slices)}.mkv"
        slice_path = os.path.join(CACHE_DIR, slice_name)

        if slice_video(video_path, actual_start, slice_duration, slice_path, skip_end):
            slices.append(slice_path)
            total_duration += slice_duration
            pool.add_used_range(video_file, actual_start, actual_start + slice_duration)

    # 最后补充不足的时长
    if total_duration < target_duration and slices:
        video_file = pool.pick_next()
        if video_file is not None:
            video_path = os.path.join(VIDEO_DIR, video_file)
            video_duration = get_media_duration(video_path)

            remaining_needed = target_duration - total_duration
            if remaining_needed > 0:
                slice_duration = min(remaining_needed, video_duration - skip_start - skip_end, max_slice)
                if slice_duration > 0:
                    max_start_time = video_duration - skip_end - slice_duration
                    actual_start = pool.pick_start_time(video_file, skip_start, max_start_time, slice_duration)

                    slice_name = f"{os.path.splitext(mp3_name)[0]}_{len(slices)}.mkv"
                    slice_path = os.path.join(CACHE_DIR, slice_name)

                    if slice_video(video_path, actual_start, slice_duration, slice_path, skip_end):
                        slices.append(slice_path)
                        total_duration += slice_duration
                        pool.add_used_range(video_file, actual_start, actual_start + slice_duration)

    logger.info(f"切片完成: {len(slices)} 个切片, 总时长 {total_duration:.1f}s, "
                f"使用了 {len(pool.video_usage_count)}/{len(video_files)} 个不同素材")

    return slices
