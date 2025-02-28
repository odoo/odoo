import sys

from argparse import ArgumentParser
from typing import List

from pdf417gen import encode, render_image


def print_usage():
    print("Usage: pdf417gen [command]")
    print("")
    print("Commands:")
    print("  help    show this help message and exit")
    print("  encode  generate a bar code from given input")
    print("")
    print("https://github.com/ihabunek/pdf417gen")


def print_err(msg: str):
    sys.stderr.write('\033[91m' + msg + '\033[0m' + "\n")


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(epilog="https://github.com/ihabunek/pdf417gen",
                            description="Generate a bar code from given input")

    parser.add_argument("text", type=str, nargs="?",
                        help="Text or data to encode. Alternatively data can be piped in.")

    parser.add_argument("-c", "--columns", dest="columns", type=int,
                        help="The number of columns (default is 6).",
                        default=6)

    parser.add_argument("-l", "--security-level", dest="security_level", type=int,
                        help="Security level (default is 2).",
                        default=2)

    parser.add_argument("-e", "--encoding", dest="encoding", type=str,
                        help="Character encoding used to decode input (default is utf-8).",
                        default='utf-8')

    parser.add_argument("-s", "--scale", dest="scale", type=int,
                        help="Module width in pixels (default is 3).",
                        default=3)

    parser.add_argument("-r", "--ratio", dest="ratio", type=int,
                        help="Module height to width ratio (default is 3).",
                        default=3)

    parser.add_argument("-p", "--padding", dest="padding", type=int,
                        help="Image padding in pixels (default is 20).",
                        default=20)

    parser.add_argument("-f", "--foreground-color", dest="fg_color", type=str,
                        help="Foreground color in hex (default is '#000000').",
                        default="#000000")

    parser.add_argument("-b", "--background-color", dest="bg_color", type=str,
                        help="Foreground color in hex (default is '#FFFFFF').",
                        default="#FFFFFF")

    parser.add_argument("-o", "--output", dest="output", type=str,
                        help="Target file (if not given, will just show the barcode).")

    return parser


def do_encode(raw_args: List[str]):
    args = get_parser().parse_args(raw_args)
    text: str = args.text

    # If no text is given, check stdin
    if not text:
        text = sys.stdin.read()

    if not text:
        print_err("No input given")
        return

    try:
        codes = encode(
            text,
            columns=args.columns,
            security_level=args.security_level,
            encoding=args.encoding,
        )

        image = render_image(
            codes,
            scale=args.scale,
            ratio=args.ratio,
            padding=args.padding,
            fg_color=args.fg_color,
            bg_color=args.bg_color,
        )
    except Exception as e:
        print_err(str(e))
        return

    if args.output:
        image.save(args.output)
    else:
        image.show()


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else None
    args = sys.argv[2:]

    if command == 'encode':
        do_encode(args)
    else:
        print_usage()
