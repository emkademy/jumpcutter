import argparse

from pathlib import Path

from jumpcutter.src.clip import Clip


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", "-i", help="Path to the input video", required=True)
    parser.add_argument(
        "--output",
        "-o",
        help="Path to where you want to save the output video. "
        "Note: Not all extensions are supported. Checkout moviepy's documentation",
        required=True,
    )
    parser.add_argument(
        "--magnitude-threshold-ratio",
        "-m",
        help="Audio signal's values ({x in R: -1 <= x <= 1}) that are: "
        "min_magnitude = min(abs(min(x)), max(x))"
        "magnitude_threshold = min_magnitude * magnitude_threshold_ratio"
        "abs(x) < magnitude_threshold"
        "will be threated as silence audio signal values.",
        type=float,
        default=0.02,
    )
    parser.add_argument(
        "--duration-threshold",
        "-d",
        help="Minimum number of required seconds in silence to cut it out",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "--failure-tolerance-ratio",
        "-f",
        help="Consequent x values are taken into account to find silence parts of the signal. "
        "Failure tolerance ratio leaves room for some error. For example if failure threshold "
        "ratio is 0.1, then in 1 second silence signal, it is allowed to have 0.1 seconds "
        "non silence signal, and it is still going to be treated as a silence signal.",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--space-on-edges",
        "-s",
        help="Leaves some space on the edges of silence cut. E.g. if it is found that there is silence "
        "between 10th and 20th second of the video, then instead of cutting it out directly, "
        "we cut out  (10+space_on_edges)th and (20-space_on_edges)th seconds of the clip",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--silence-part-speed",
        "-x",
        help="If this parameter is set, it will speed up the silence parts x times instead of cutting them out",
        type=int,
        required=False,
    )
    parser.add_argument(
        "--min-loud-part-duration",
        "-l",
        help="If this parameter is set, loud parts of the clip that are shorter than this parameter "
        "(in seconds) will also be cutted",
        type=int,
        required=False,
        default=-1,
    )

    args = parser.parse_args()
    print("Running with the arguments:")
    print(args)
    print(60 * "-")
    if args.duration_threshold / 2 <= args.space_on_edges:
        print(60 * "*")
        print("WARNING:")
        print(
            "You have selected space_on_edges >= duration_threshold/2. This may cause overlapping sequences"
        )
        print(60 * "*")

    input_path = (
        args.input if Path(args.input).is_absolute() else Path().cwd() / args.input
    )
    output_path = (
        args.output if Path(args.output).is_absolute() else Path().cwd() / args.output
    )

    clip = Clip(str(input_path))
    jumpcutted_clip, _ = clip.jumpcut(
        args.magnitude_threshold_ratio,
        args.duration_threshold,
        args.failure_tolerance_ratio,
        args.space_on_edges,
        args.silence_part_speed,
        args.min_loud_part_duration,
    )
    jumpcutted_clip.write_videofile(str(output_path))


if __name__ == "__main__":
    main()
