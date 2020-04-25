## What is jumpcutter?

Jumpcutter is a program that is written in Python to automatically jump-cut silent parts of your videos.
The purpose here is to ease your post recording work.

Check out [the medium post](https://medium.com/@emkademy/how-to-jump-cut-silent-parts-of-your-videos-automatically-with-python-2e4b96320dc1)
for more information.

## Installation
You can install jumpcutter by simply:

```bash
pip install jumpcutter 
```

## Demo

[![Watch the video](https://img.youtube.com/vi/UDjzm_lzWOA/hqdefault.jpg)](https://youtu.be/UDjzm_lzWOA)

## How to run it?
There are 8 command line arguments you can run the program with. 
Before explaining them, I would like to say that most of these parameters 
have a default value that “just works”. So, if you don’t want you don’t need to specify 
(or know) almost any of these parameters. You will be just fine with the default values.

1. `--input`, `-i`: Path to the video that you want to jump-cut.
2. `--output`, `-o`: Path to where you want to save the output video.
3. `--magnitude-threshold-ratio`, `-m`: The percentage of the maximum value of your audio signal that you would like to 
     consider as silent a signal (default: 0.02).
4. `--duration-threshold`, `-d`: Minimum number of required seconds in silence to cut it out. For example if this parameter 
     is 0.5, it means that the silence parts have to last minimum 0.5 seconds, otherwise they won't be jump-cut (default: 0.5).
5. `--failure-tolerance-ratio`, `-f`: Most of the times, there are 44100 audio signal values in 1 second of a video. 
     Let's say the "--duration-threshold" was set to 0.5. This means that, we need to check minimum 22050 signal 
     values to see if there is a silent part of not. What happens if we found 22049 values that we consider as silent, 
     but there is 1 value that is above our threshold. Should we just throw this part of the video and consider it as a 
     loud signal? I think we shouldn't. This parameter leaves some room for failure, it tolerates high signal values until 
     some point. Let's say it is set to 0.1, it means that 10% of the signal that is currently being investigated can 
     have values that are higher than our threshold, but they are still going to be considered as a silent part (default: 0.1).
6. `--spaces-on-edges`, `-s`: Leaves some space on the edges of silence cut. E.g. if it is found that there is 
     silence between 10th and 20th second of the video, then instead of cutting it out directly, we cut out 
     (10+space_on_edges)th and (20-space_on_edges)th seconds of the clip (default: 0.1).
7. `--silence-part-speed`, `-x`: If this parameter is given, instead of cutting the silent parts out, the script will 
     speed them up "x" times.
8. `--min-loud-part-duration`, `-l`: If this parameter is given, loud parts of the video that are shorter then this 
     parameter will also be cut.
     
## Examples of running the program

```bash
# The simplest way you can run the program
jumpcutter -i input_video.mp4 -o output_video.mp4
# If you want, you can also set the other parameters that was mentioned
jumpcutter -i input_video.mp4 -o output_video.mp4 -m 0.05 -d 1.0 -f 0.2 -s 0.2 -x 2000 -l 1.0
```
