import argparse
import dataclasses
import sys
from pathlib import Path

from domain_types_linter.config import find_config, load_config
from domain_types_linter.main import scan_path


def main():
    """Entry point for the command-line interface.

    Parses command-line arguments, runs the linter on the specified path,
    and exits with code 1 if problems are found.
    """
    parser = argparse.ArgumentParser(description="Domain Types Linter")
    parser.add_argument("path", help="Path to the file or directory to check")
    parser.add_argument(
        "--config",
        help="Path to pyproject.toml with the [tool.domain-types-linter] section "
        "(by default the closest one to the checked path is used)",
    )
    parser.add_argument(
        "--frequent",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Report only names that are annotated with universal types often",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        help="Frequent mode: minimum number of annotations of a name to report it (default 3)",
    )
    parser.add_argument(
        "--min-modules",
        type=int,
        help="Frequent mode: minimum number of modules a name must appear in (default 1)",
    )
    args = parser.parse_args()

    try:
        config = load_config(Path(args.config)) if args.config else find_config(Path(args.path))
    except (OSError, ValueError) as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(2)

    overrides = {
        "frequent": args.frequent,
        "min_occurrences": args.min_occurrences,
        "min_modules": args.min_modules,
    }
    config = dataclasses.replace(config, **{k: v for k, v in overrides.items() if v is not None})

    problems_found = scan_path(args.path, config)

    if any(problems for _, problems in problems_found):
        sys.exit(1)

    print("All checks have been successful!")
