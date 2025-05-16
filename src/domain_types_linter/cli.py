import argparse
import sys

from domain_types_linter.main import scan_path


def main():
    """Entry point for the command-line interface.

    Parses command-line arguments, runs the linter on the specified path,
    and exits with code 1 if problems are found.
    """
    parser = argparse.ArgumentParser(description="Domain Types Linter")
    parser.add_argument("path", help="Path to the file or directory to check")
    args = parser.parse_args()

    problems_found = scan_path(args.path)

    if problems_found:
        sys.exit(1)

    print("All checks have been successful!")
