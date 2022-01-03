import numpy as np

from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.fx.all import speedx
from tqdm import tqdm


class Clip:
    def __init__(self, clip_path, min_loud_part_duration, silence_part_speed):
        self.clip = VideoFileClip(clip_path)
        self.audio = Audio(self.clip.audio)
        self.cut_to_method = {
            "silent": self.jumpcut_silent_parts,
            "voiced": self.jumpcut_voiced_parts,
        }
        self.min_loud_part_duration = min_loud_part_duration
        self.silence_part_speed = silence_part_speed

    def get_duration(self):
        return self.clip.duration

    def jumpcut(
        self,
        cuts,
        magnitude_threshold_ratio,
        duration_threshold_in_seconds,
        failure_tolerance_ratio,
        space_on_edges,
    ):

        intervals_to_cut = self.audio.get_intervals_to_cut(
            magnitude_threshold_ratio,
            duration_threshold_in_seconds,
            failure_tolerance_ratio,
            space_on_edges,
        )
        outputs = {}
        for cut in cuts:
            jumpcutted_clips = self.cut_to_method[cut](intervals_to_cut)
            outputs[cut] = concatenate_videoclips(jumpcutted_clips)

        return outputs

    def jumpcut_silent_parts(self, intervals_to_cut):
        jumpcutted_clips = []
        previous_stop = 0
        for start, stop in tqdm(intervals_to_cut, desc="Cutting silent intervals"):
            clip_before = self.clip.subclip(previous_stop, start)

            if clip_before.duration > self.min_loud_part_duration:
                jumpcutted_clips.append(clip_before)

            if self.silence_part_speed is not None:
                silence_clip = self.clip.subclip(start, stop)
                silence_clip = speedx(
                    silence_clip, self.silence_part_speed
                ).without_audio()
                jumpcutted_clips.append(silence_clip)

            previous_stop = stop

        if previous_stop < self.clip.duration:
            last_clip = self.clip.subclip(previous_stop, self.clip.duration)
            jumpcutted_clips.append(last_clip)
        return jumpcutted_clips

    def jumpcut_voiced_parts(self, intervals_to_cut):
        jumpcutted_clips = []
        for start, stop in tqdm(intervals_to_cut, desc="Cutting voiced intervals"):
            if start < stop:
                silence_clip = self.clip.subclip(start, stop)
                jumpcutted_clips.append(silence_clip)
        return jumpcutted_clips


class Audio:
    def __init__(self, audio):
        self.audio = audio
        self.fps = audio.fps

        self.signal = self.audio.to_soundarray()
        if len(self.signal.shape) == 1:
            self.signal = self.signal.reshape(-1, 1)

    def get_intervals_to_cut(
        self,
        magnitude_threshold_ratio,
        duration_threshold_in_seconds,
        failure_tolerance_ratio,
        space_on_edges,
    ):
        min_magnitude = min(abs(np.min(self.signal)), np.max(self.signal))
        magnitude_threshold = min_magnitude * magnitude_threshold_ratio
        failure_tolerance = self.fps * failure_tolerance_ratio
        duration_threshold = self.fps * duration_threshold_in_seconds
        silence_counter = 0
        failure_counter = 0

        intervals_to_cut = []
        absolute_signal = np.absolute(self.signal)
        for i, values in tqdm(
            enumerate(absolute_signal),
            desc="Getting silent intervals to cut",
            total=len(absolute_signal),
        ):
            silence = all([value < magnitude_threshold for value in values])
            silence_counter += silence
            failure_counter += not silence
            if failure_counter >= failure_tolerance:
                if silence_counter >= duration_threshold:
                    interval_end = (i - failure_counter) / self.fps
                    interval_start = interval_end - (silence_counter / self.fps)

                    interval_start += space_on_edges
                    interval_end -= space_on_edges

                    intervals_to_cut.append(
                        (abs(interval_start), interval_end)
                    )  # in seconds
                silence_counter = 0
                failure_counter = 0
        return intervals_to_cut
