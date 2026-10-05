import ast
from pathlib import Path
from typing import Dict, Generator, List, Tuple, Type

from domain_types_linter.config import Config, find_config
from domain_types_linter.main import Linter

# Configs found for directories, so that pyproject.toml is not re-read for every file.
_config_cache: Dict[Path, Config] = {}


def get_config(filename: str) -> Config:
    """Get the config from the closest pyproject.toml for the file being checked."""
    if filename and filename not in ("stdin", "-"):
        directory = Path(filename).resolve().parent
    else:
        directory = Path.cwd()

    if directory not in _config_cache:
        _config_cache[directory] = find_config(directory)

    return _config_cache[directory]


class DomainTypesLinter:
    """
    Flake8 plugin for checking domain type violations.

    This class implements the Flake8 plugin interface for the domain types linter.
    It checks that code in the business logic layer uses only explicit business logic objects,
    not universal types.

    Settings are read from the [tool.domain-types-linter] section of pyproject.toml.
    The frequent mode is not supported, because flake8 checks files one by one.
    """

    name = "domain-types-linter"
    version = "1.0.0"
    code_prefix = "DT"

    def __init__(self, tree: ast.AST, filename: str = "", lines: List[str] = None) -> None:
        self.tree = tree
        self.filename = filename
        self.source_lines = lines or []

    def run(self) -> Generator[Tuple[int, int, str, Type], None, None]:
        """Run the linter on the AST tree and yield problems."""
        config = get_config(self.filename)
        if self.filename and not config.is_file_included(self.filename):
            return

        # flake8 passes lines with line endings, the linter expects them without.
        source_lines = [line.rstrip("\r\n") for line in self.source_lines]

        linter = Linter(source_lines, self.filename, config)
        linter.visit(self.tree)

        for error in linter.problems:
            # Convert our error format to flake8 format
            line_number = error.line_number
            column = 0  # We don't track column numbers in our linter
            error_code = error.get_problem_code()
            message = error.get_problem_message()

            # Yield the error in the format expected by flake8
            yield line_number, column, f"{error_code} {message}", type(self)
