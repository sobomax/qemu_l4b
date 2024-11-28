from sys import stderr, exit as s_exit
from argparse import ArgumentParser

from StructDefFinder import StructDefFinder

def main():
    parser = ArgumentParser(description="Process a directory with optional config and debug mode.")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-header', action='store_true', help='Disable header')
    parser.add_argument('directory_path', help='Path to directory')
    parser.add_argument('config_file', help='Path to config file')

    args = parser.parse_args()
    directory = args.directory_path
    config_file = args.config_file
    debug = args.debug
    no_header = args.no_header

    structs = []
    defines = []
    try:
        with open(config_file, 'r') as f:
            config = eval(f.read())
            if not isinstance(config, dict):
                raise ValueError("Config file must contain a dictionary.")
    except Exception as e:
        print(f"Error reading config file: {e}", file=stderr)
        s_exit(1)

    finder = StructDefFinder(config, directory, debug=debug, no_header=no_header)
    finder.find_in_dir(is_top_level=True)
    finder.print_results()


if __name__ == "__main__":
    main()
