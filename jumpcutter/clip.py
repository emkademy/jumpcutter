import os
import xml.etree.cElementTree as ElementTree

from typing import Dict, List, Tuple

import numpy as np

from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.fx.all import speedx
from moviepy.video.io.VideoFileClip import VideoFileClip
from tqdm import tqdm


class Clip:
    def __init__(
        self, clip_path: str, min_loud_part_duration: int, silence_part_speed: int
    ) -> None:
        self.clip = VideoFileClip(clip_path)
        self.audio = Audio(self.clip.audio)
        self.cut_to_method = {
            "silent": self.jumpcut_silent_parts,
            "voiced": self.jumpcut_voiced_parts,
        }
        self.min_loud_part_duration = min_loud_part_duration
        self.silence_part_speed = silence_part_speed

    def jumpcut(
        self,
        cuts: List[str],
        magnitude_threshold_ratio: float,
        duration_threshold_in_seconds: float,
        failure_tolerance_ratio: float,
        space_on_edges: float,
    ) -> Dict[str, VideoFileClip]:

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

    def jumpcut_silent_parts(
        self, intervals_to_cut: List[Tuple[float, float]]
    ) -> List[VideoFileClip]:
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

    def jumpcut_voiced_parts(
        self, intervals_to_cut: List[Tuple[float, float]]
    ) -> List[VideoFileClip]:
        jumpcutted_clips = []
        for start, stop in tqdm(intervals_to_cut, desc="Cutting voiced intervals"):
            if start < stop:
                silence_clip = self.clip.subclip(start, stop)
                jumpcutted_clips.append(silence_clip)
        return jumpcutted_clips


class Audio:
    def __init__(self, audio: AudioFileClip) -> None:
        self.audio = audio
        self.fps = audio.fps

        self.signal = self.audio.to_soundarray()
        if len(self.signal.shape) == 1:
            self.signal = self.signal.reshape(-1, 1)

    def get_intervals_to_cut(
        self,
        magnitude_threshold_ratio: float,
        duration_threshold_in_seconds: float,
        failure_tolerance_ratio: float,
        space_on_edges: float,
    ) -> List[Tuple[float, float]]:
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


class xmlGen:
    def __init__(
        self,
        clip_path,
        out_file,
        magnitude_threshold_ratio,
        duration_threshold,
        failure_tolerance_ratio,
        space_on_edges,
        min_loud_part_duration,
        cutType,
        audioChannels=1,
    ):
        self.audioChannels = audioChannels
        self.clip_path = clip_path
        self.clip = VideoFileClip(clip_path)
        self.audio = Audio(self.clip.audio)
        head, tail = os.path.split(clip_path)
        self.folder = head
        self.clipName = tail
        self.out_file = out_file
        self.firstClip = True
        self.fps = self.clip.fps
        self.width = self.clip.size[0]
        self.height = self.clip.size[1]
        self.audChan = audioChannels * 2
        self.magnitude_threshold_ratio = magnitude_threshold_ratio
        self.duration_threshold = duration_threshold
        self.failure_tolerance_ratio = failure_tolerance_ratio
        self.space_on_edges = space_on_edges
        self.min_loud_part_duration = min_loud_part_duration
        self.cutType = cutType
        self.clipNumber = 0
        self.curFrame = 0
        self.clipcount = 0
        self.getCuts()
        self.getDuration()
        self.makeXML()
        self.export()

    def getCuts(self):
        self.fullClipDurration = self.clip.duration * self.fps
        intervals_to_cut = self.audio.get_intervals_to_cut(
            self.magnitude_threshold_ratio,
            self.duration_threshold,
            self.failure_tolerance_ratio,
            self.space_on_edges,
        )
        self.cuts = []
        previous_stop = 0
        for start, stop in intervals_to_cut:
            silentClip = (start, stop)
            prevLoudClip = None
            loudDur = start - previous_stop
            if loudDur > self.min_loud_part_duration:

                prevLoudClip = (previous_stop, start)
            else:
                silentClip = (previous_stop, stop)
            if self.cutType == "silent":
                if prevLoudClip is not None:
                    self.cuts.append(prevLoudClip)
            elif self.cutType == "voiced":
                self.cuts.append(silentClip)
            else:
                if prevLoudClip is not None:
                    self.cuts.append(prevLoudClip)
                self.cuts.append(silentClip)
            previous_stop = stop
        if self.cutType == "silent":
            lastLoudClip = (stop, self.clip.duration)
            self.cuts.append(lastLoudClip)

    def getDuration(self):
        self.durations = []
        self.frameCuts = []
        for clips in self.cuts:
            framCut = (int(clips[0] * 60), int(clips[1] * 60))
            self.frameCuts.append(framCut)
            self.durations.append(int(framCut[1] - framCut[0]))

        self.duration = int(sum(self.durations))

    def makeXML(self):
        self.tree = ElementTree.Element("xmeml", {"version": "5"})
        seq = ElementTree.SubElement(self.tree, "sequence")
        name = ElementTree.SubElement(seq, "name").text = (
            os.path.splitext(self.clipName)[0] + " Split"
        )
        ElementTree.SubElement(seq, "duration").text = str(self.duration)
        self.addRate(seq)
        ElementTree.SubElement(seq, "in").text = str(-1)
        ElementTree.SubElement(seq, "out").text = str(-1)
        tc = ElementTree.SubElement(seq, "timecode")
        ElementTree.SubElement(tc, "string").text = "01:00:00:00"
        ElementTree.SubElement(tc, "frame").text = "216000"
        ElementTree.SubElement(tc, "displayformat").text = "NDF"
        self.addRate(tc)
        med = ElementTree.SubElement(seq, "media")
        video = ElementTree.SubElement(med, "video")
        vt = ElementTree.SubElement(video, "track")
        self.setVideoFormat(video)
        audio = ElementTree.SubElement(med, "audio")
        ats = []
        for i in range(self.audioChannels):
            ats.append(ElementTree.SubElement(audio, "track"))
        for cuts in self.frameCuts:
            self.clipcount += 1
            linkedTracks = {}
            linkedTracks["video"] = "{} {}".format(self.clipName, self.clipNumber)
            linkedTracks["audio"] = []
            for i in range(self.audioChannels):
                linkedTracks["audio"].append(
                    "{} {}".format(self.clipName, self.clipNumber + 1 + i)
                )
            self.addVideoTrack(vt, cuts, linkedTracks)
            trackindex = 0
            for at in ats:

                self.clipNumber += 1
                trackindex += 1
                clipName = linkedTracks["audio"][trackindex - 1]
                self.addAudioTrack(
                    at, cuts, clipName, linkedTracks, trackindex=trackindex
                )
            self.curFrame += cuts[1] - cuts[0]
            self.clipNumber += 1
        ElementTree.SubElement(at, "enabled").text = "TRUE"
        ElementTree.SubElement(at, "locked").text = "FALSE"

    def addAudioTrack(self, vt, cuts, clipName, linkedTracks, trackindex=1):
        clipItem = ElementTree.SubElement(vt, "clipitem", {"id": clipName})
        ElementTree.SubElement(clipItem, "name").text = self.clipName
        ElementTree.SubElement(clipItem, "duration").text = str(self.fullClipDurration)
        self.addRate(clipItem)
        ElementTree.SubElement(clipItem, "start").text = str(self.curFrame)
        ElementTree.SubElement(clipItem, "stop").text = str(
            self.curFrame + cuts[1] - cuts[0]
        )
        ElementTree.SubElement(clipItem, "enabled").text = "TRUE"
        ElementTree.SubElement(clipItem, "in").text = str(cuts[0])
        ElementTree.SubElement(clipItem, "out").text = str(cuts[1])
        ElementTree.SubElement(
            clipItem, "file", {"id": "{} {}".format(self.clipName, "vid")}
        )
        sourceTrack = ElementTree.SubElement(clipItem, "sourcetrack")
        ElementTree.SubElement(sourceTrack, "mediatype").text = "audio"
        ElementTree.SubElement(sourceTrack, "trackindex").text = str(trackindex)

        vidLink = ElementTree.SubElement(clipItem, "link")
        ElementTree.SubElement(vidLink, "linkclipref").text = linkedTracks["video"]
        ElementTree.SubElement(vidLink, "mediatype").text = "video"

        for audioLink in linkedTracks["audio"]:
            lin = ElementTree.SubElement(clipItem, "link")
            ElementTree.SubElement(lin, "linkclipref").text = audioLink
            ElementTree.SubElement(lin, "mediatype").text = "audio"

    def addVideoTrack(self, vt, cuts, linkedTracks):
        clipItem = ElementTree.SubElement(
            vt, "clipitem", {"id": "{} {}".format(self.clipName, self.clipNumber)}
        )

        ElementTree.SubElement(clipItem, "name").text = self.clipName
        ElementTree.SubElement(clipItem, "duration").text = str(self.fullClipDurration)
        self.addRate(clipItem)
        ElementTree.SubElement(clipItem, "start").text = str(self.curFrame)

        ElementTree.SubElement(clipItem, "stop").text = str(
            self.curFrame + cuts[1] - cuts[0]
        )

        ElementTree.SubElement(clipItem, "enabled").text = "TRUE"
        ElementTree.SubElement(clipItem, "in").text = str(cuts[0])
        ElementTree.SubElement(clipItem, "out").text = str(cuts[1])
        file = ElementTree.SubElement(
            clipItem, "file", {"id": "{} {}".format(self.clipName, "vid")}
        )
        if self.firstClip:
            ElementTree.SubElement(file, "duration").text = str(self.fullClipDurration)
            self.addRate(file)
            ElementTree.SubElement(file, "out").text = self.clipName
            pathToFile = "file://localhost/{}".format(
                "/".join(os.path.split(self.clip_path))
            )
            ElementTree.SubElement(file, "pathurl").text = pathToFile
            tc = ElementTree.SubElement(file, "timecode")
            ElementTree.SubElement(tc, "string").text = "00:00:00:00"
            ElementTree.SubElement(tc, "displayformat").text = "NDF"
            self.addRate(tc)
            med = ElementTree.SubElement(file, "media")
            vid = ElementTree.SubElement(med, "video")
            ElementTree.SubElement(vid, "duration").text = str(self.fullClipDurration)
            sc = ElementTree.SubElement(vid, "samplecharacteristics")
            ElementTree.SubElement(sc, "width").text = str(self.width)
            ElementTree.SubElement(sc, "height").text = str(self.height)
            aud = ElementTree.SubElement(med, "audio")
            ElementTree.SubElement(aud, "channelcount").text = str(self.audChan)
            firstClip = False
        ElementTree.SubElement(clipItem, "compositemode").text = "normal"
        ##Filter to play the video

        filt1 = ElementTree.SubElement(clipItem, "filter")
        ElementTree.SubElement(filt1, "enabled").text = "TRUE"
        ElementTree.SubElement(filt1, "start").text = "0"
        ElementTree.SubElement(filt1, "end").text = str(self.fullClipDurration)
        eff1 = ElementTree.SubElement(filt1, "effect")
        ElementTree.SubElement(eff1, "name").text = "Basic Motion"
        ElementTree.SubElement(eff1, "effectid").text = "basic"
        ElementTree.SubElement(eff1, "effecttype").text = "motion"
        ElementTree.SubElement(eff1, "mediatype").text = "video"
        ElementTree.SubElement(eff1, "effectcategory").text = "motion"
        parm1a = ElementTree.SubElement(eff1, "parameter")
        ElementTree.SubElement(parm1a, "name").text = "Scale"
        ElementTree.SubElement(parm1a, "parameterid").text = "scale"
        ElementTree.SubElement(parm1a, "value").text = "100"
        ElementTree.SubElement(parm1a, "valuemin").text = "0"
        ElementTree.SubElement(parm1a, "valuemax").text = "10000"
        parm1b = ElementTree.SubElement(eff1, "parameter")
        ElementTree.SubElement(parm1b, "name").text = "Center"
        ElementTree.SubElement(parm1b, "parameterid").text = "center"
        parm1bval = ElementTree.SubElement(parm1b, "value")
        ElementTree.SubElement(parm1bval, "horiz").text = "0"
        ElementTree.SubElement(parm1bval, "vert").text = "0"
        parm1c = ElementTree.SubElement(eff1, "parameter")
        ElementTree.SubElement(parm1c, "name").text = "Rotation"
        ElementTree.SubElement(parm1c, "parameterid").text = "rotation"
        ElementTree.SubElement(parm1c, "value").text = "0"
        ElementTree.SubElement(parm1c, "valuemin").text = "-100000"
        ElementTree.SubElement(parm1c, "valuemax").text = "100000"
        parm1d = ElementTree.SubElement(eff1, "parameter")
        ElementTree.SubElement(parm1d, "name").text = "Anchor Point"
        ElementTree.SubElement(parm1d, "parameterid").text = "centerOffset"
        parm1dval = ElementTree.SubElement(parm1d, "value")
        ElementTree.SubElement(parm1dval, "horiz").text = "0"
        ElementTree.SubElement(parm1dval, "vert").text = "0"
        ##Filter to crop
        filt2 = ElementTree.SubElement(clipItem, "filter")
        ElementTree.SubElement(filt2, "enabled").text = "TRUE"
        ElementTree.SubElement(filt2, "start").text = "0"
        ElementTree.SubElement(filt2, "end").text = str(self.fullClipDurration)
        eff2 = ElementTree.SubElement(filt2, "effect")
        ElementTree.SubElement(eff2, "name").text = "Crop"
        ElementTree.SubElement(eff2, "effectid").text = "crop"
        ElementTree.SubElement(eff2, "effecttype").text = "motion"
        ElementTree.SubElement(eff2, "mediatype").text = "video"
        ElementTree.SubElement(eff2, "effectcategory").text = "motion"
        parm2a = ElementTree.SubElement(eff2, "parameter")
        ElementTree.SubElement(parm2a, "name").text = "left"
        ElementTree.SubElement(parm2a, "parameterid").text = "left"
        ElementTree.SubElement(parm2a, "value").text = "0"
        ElementTree.SubElement(parm2a, "valuemin").text = "0"
        ElementTree.SubElement(parm2a, "valuemax").text = "100"
        parm2b = ElementTree.SubElement(eff2, "parameter")
        ElementTree.SubElement(parm2b, "name").text = "right"
        ElementTree.SubElement(parm2b, "parameterid").text = "right"
        ElementTree.SubElement(parm2b, "value").text = "0"
        ElementTree.SubElement(parm2b, "valuemin").text = "0"
        ElementTree.SubElement(parm2b, "valuemax").text = "100"
        parm2b = ElementTree.SubElement(eff2, "parameter")
        ElementTree.SubElement(parm2b, "name").text = "top"
        ElementTree.SubElement(parm2b, "parameterid").text = "top"
        ElementTree.SubElement(parm2b, "value").text = "0"
        ElementTree.SubElement(parm2b, "valuemin").text = "0"
        ElementTree.SubElement(parm2b, "valuemax").text = "100"
        parm2b = ElementTree.SubElement(eff2, "parameter")
        ElementTree.SubElement(parm2b, "name").text = "bottom"
        ElementTree.SubElement(parm2b, "parameterid").text = "bottom"
        ElementTree.SubElement(parm2b, "value").text = "0"
        ElementTree.SubElement(parm2b, "valuemin").text = "0"
        ElementTree.SubElement(parm2b, "valuemax").text = "100"
        ##Filter to set opacity
        filt3 = ElementTree.SubElement(clipItem, "filter")
        ElementTree.SubElement(filt3, "enabled").text = "TRUE"
        ElementTree.SubElement(filt3, "start").text = "0"
        ElementTree.SubElement(filt3, "end").text = str(self.fullClipDurration)
        eff3 = ElementTree.SubElement(filt3, "effect")
        ElementTree.SubElement(eff3, "name").text = "Opacity"
        ElementTree.SubElement(eff3, "effectid").text = "opacity"
        ElementTree.SubElement(eff3, "effecttype").text = "motion"
        ElementTree.SubElement(eff3, "mediatype").text = "video"
        ElementTree.SubElement(eff3, "effectcategory").text = "motion"
        parm3a = ElementTree.SubElement(eff3, "parameter")
        ElementTree.SubElement(parm3a, "name").text = "opacity"
        ElementTree.SubElement(parm3a, "parameterid").text = "opacity"
        ElementTree.SubElement(parm3a, "value").text = "100"
        ElementTree.SubElement(parm3a, "valuemin").text = "0"
        ElementTree.SubElement(parm3a, "valuemax").text = "100"

        vidLink = ElementTree.SubElement(clipItem, "link")
        ElementTree.SubElement(vidLink, "linkclipref").text = linkedTracks["video"]

        for audioLink in linkedTracks["audio"]:
            lin = ElementTree.SubElement(clipItem, "link")
            ElementTree.SubElement(lin, "linkclipref").text = audioLink

    def setVideoFormat(self, video):
        form = ElementTree.SubElement(video, "format")
        sampChar = ElementTree.SubElement(form, "samplecharacteristics")
        ElementTree.SubElement(sampChar, "width").text = str(self.width)
        ElementTree.SubElement(sampChar, "height").text = str(self.height)
        ElementTree.SubElement(sampChar, "pixelaspectratio").text = "square"
        self.addRate(sampChar)
        codec = ElementTree.SubElement(sampChar, "codec")
        appData = ElementTree.SubElement(codec, "appspecificdata")
        ElementTree.SubElement(appData, "appname").text = "Final Cut Pro"
        ElementTree.SubElement(appData, "appmanufacturer").text = "Apple Inc."
        data = ElementTree.SubElement(appData, "data")
        ElementTree.SubElement(data, "qtcodec")

    def addRate(self, root):
        rat = ElementTree.SubElement(root, "rate")
        ElementTree.SubElement(rat, "timebase").text = str(self.fps)
        ElementTree.SubElement(rat, "ntsc").text = "FALSE"

    def export(self):
        with open(self.out_file, "wb") as f:
            f.write(
                '<?xml version="1.0" encoding="UTF-8" ?>\n<!DOCTYPE xmeml>\n'.encode(
                    "utf8"
                )
            )
            ElementTree.indent(self.tree, space="\t", level=0)
            ElementTree.ElementTree(self.tree).write(f, "utf-8")
