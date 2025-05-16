import ast
from typing import Generator, List, Tuple, Type

from domain_types_linter.main import Linter


class DomainTypesLinter:
    """
    Flake8 plugin for checking domain type violations.

    This class implements the Flake8 plugin interface for the domain types linter.
    It checks that code in the business logic layer uses only explicit business logic objects,
    not universal types.
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
        linter = Linter(self.source_lines, self.filename)
        linter.visit(self.tree)

        for error in linter.problems:
            # Convert our error format to flake8 format
            line_number = error.line_number
            column = 0  # We don't track column numbers in our linter
            error_code = error.get_problem_code()
            message = error.get_problem_message()

            # Yield the error in the format expected by flake8
            yield line_number, column, f"{error_code} {message}", type(self)
