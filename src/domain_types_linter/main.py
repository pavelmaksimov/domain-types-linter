import ast
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Tuple, Optional

from domain_types_linter.types_and_codes import (
    ALIAS_TYPE_CODE,
    TYPE_CODES,
    DISALLOWED_BASE_TYPES,
    DISALLOWED_GENERIC_TYPES,
    ALLOWED_GENERIC_TYPES,
)


class ProblemType(Enum):
    """Enum representing different types of problems that can be detected by the linter.

    Attributes:
        ALIAS_USAGE: Using an alias for a universal type (e.g., alias_str = str)
        BASE_TYPE_USAGE: Using a universal base type directly (e.g., str, int)
        GENERIC_TYPE_WITHOUT_PARAMS: Using a generic type without domain-specific parameters
    """

    ALIAS_USAGE = auto()
    BASE_TYPE_USAGE = auto()
    GENERIC_TYPE_WITHOUT_PARAMS = auto()


@dataclass
class Problem:
    """Represents a problem found by the linter.

    This dataclass stores information about a detected problem, including its location,
    type, and relevant context information.

    Attributes:
        line_number: Line number where the problem was found
        problem_type: Type of the problem (from ProblemType enum)
        type_name: Name of the type that caused the problem
        filepath: Path to the file where the problem was found
        object_type: Type of the AST object where the problem was found
        code_line: The actual line of code containing the problem
    """

    line_number: int
    problem_type: ProblemType
    type_name: str
    filepath: str
    object_type: str = ""
    code_line: str = ""

    def __str__(self) -> str:
        code = self.get_problem_code()
        message = self.get_problem_message()
        line_info = f"{self.filepath}:{self.line_number}: {code} {message}"
        return line_info

    def get_problem_code(self) -> str:
        if self.problem_type == ProblemType.ALIAS_USAGE:
            return ALIAS_TYPE_CODE

        type_lower = self.type_name.lower()

        return TYPE_CODES.get(type_lower, "DT999")

    def get_problem_message(self) -> str:
        if self.problem_type == ProblemType.ALIAS_USAGE:
            return f"forbidden to use alias with universal type '{self.type_name}'"

        elif self.problem_type == ProblemType.BASE_TYPE_USAGE:
            return f"forbidden to use universal type '{self.type_name}'"

        elif self.problem_type == ProblemType.GENERIC_TYPE_WITHOUT_PARAMS:
            return f"forbidden to use parameterized type without domain type '{self.type_name}'"

        else:
            raise ValueError(f"Unknown problem type: {self.problem_type}")


class Linter(ast.NodeVisitor):
    """AST visitor that checks for domain type violations.

    This class traverses the AST of a Python file and identifies violations of domain type rules,
    such as using universal types directly or using generic types without proper domain-specific parameters.

    Attributes:
        problems: List of detected problems
        aliases: Set of user-defined aliases for universal types
        source_lines: Source code lines of the file being analyzed
        filepath: Path to the file being analyzed
    """

    def __init__(self, source_lines: Optional[List[str]] = None, filepath: str = ""):
        """
        Args:
            source_lines: List of source code lines (optional)
            filepath: Path to the file being analyzed (optional)
        """
        self.problems: List[Problem] = []
        # Set of user-defined aliases (e.g., alias_str derived from alias_str = str)
        self.aliases: set[str] = set()
        self.source_lines: List[str] = source_lines if source_lines is not None else []
        self.filepath: str = filepath

    def record_problem(self, node: ast.AST, problem_type: ProblemType, type_name: str) -> None:
        """Record a problem found during AST traversal.

        Args:
            node: The AST node where the problem was found
            problem_type: Type of the problem (from ProblemType enum)
            type_name: Name of the type that caused the problem
        """
        lineno = getattr(node, "lineno", 0)

        # Determine the object type
        object_type = type(node).__name__

        # Get the code line if available
        code_line = ""
        if self.source_lines and 0 < lineno <= len(self.source_lines):
            code_line = self.source_lines[lineno - 1]

        problem = Problem(
            line_number=lineno,
            problem_type=problem_type,
            type_name=type_name,
            object_type=object_type,
            code_line=code_line,
            filepath=self.filepath,
        )
        self.problems.append(problem)

    def visit_Module(self, node: ast.Module) -> None:
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Process assignment nodes in the AST.

        If an assignment of the form `alias_str = str` is found,
        it is allowed, and the alias name is stored in self.aliases.
        """
        if isinstance(node.value, ast.Name) and node.value.id in DISALLOWED_BASE_TYPES:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.aliases.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit an annotated assignment node.

        Checks the type annotation in the assignment.
        """
        if node.annotation:
            self.check_annotation(node.annotation)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition node.

        Checks the return type annotation and argument type annotations.
        """
        if node.returns:
            self.check_annotation(node.returns)
        for arg in node.args.args:
            if arg.annotation:
                self.check_annotation(arg.annotation)

        self.generic_visit(node)

    def check_annotation(self, annotation: ast.expr) -> None:
        """Check a type annotation for domain type violations.

        Recursively checks type annotations for violations of domain type rules.
        """
        if isinstance(annotation, ast.Name):
            if annotation.id in self.aliases:
                self.record_problem(
                    annotation,
                    ProblemType.ALIAS_USAGE,
                    annotation.id,
                )

            elif annotation.id in DISALLOWED_BASE_TYPES:
                self.record_problem(
                    annotation,
                    ProblemType.BASE_TYPE_USAGE,
                    annotation.id,
                )

            elif annotation.id in DISALLOWED_GENERIC_TYPES:
                self.record_problem(
                    annotation,
                    ProblemType.GENERIC_TYPE_WITHOUT_PARAMS,
                    annotation.id,
                )

        elif isinstance(annotation, ast.Subscript):
            outer_type = annotation.value
            inner_annotation = annotation.slice

            if isinstance(outer_type, ast.Name):
                type_name = outer_type.id

                if type_name in DISALLOWED_GENERIC_TYPES:
                    if not self.has_parameters(annotation):
                        self.record_problem(
                            outer_type,
                            ProblemType.GENERIC_TYPE_WITHOUT_PARAMS,
                            type_name,
                        )

                    self.check_annotation(inner_annotation)

                elif type_name in ALLOWED_GENERIC_TYPES:
                    self.check_annotation(inner_annotation)

                else:
                    self.check_annotation(inner_annotation)

            else:
                self.check_annotation(outer_type)
                self.check_annotation(inner_annotation)

        # Checking the association of types through the operator "|" (Python 3.10+).
        elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            self.check_annotation(annotation.left)
            self.check_annotation(annotation.right)

        # If the annotation is a motorcade, for example: tuple [int, str, ...].
        elif isinstance(annotation, ast.Tuple):
            for elt in annotation.elts:
                self.check_annotation(elt)

        # Calls processing (for example, Newtype ("Userid", Int)).
        elif isinstance(annotation, ast.Call):
            for arg in annotation.args:
                self.check_annotation(arg)

        # If the annotation is represented through Attribute, for example: Module.type
        elif isinstance(annotation, ast.Attribute):
            full_name = self.get_full_attr_name(annotation)

            # We check if the attribute ends on the prohibited basic type.
            for disallowed in DISALLOWED_BASE_TYPES:
                if full_name.endswith(disallowed):
                    self.record_problem(
                        annotation,
                        ProblemType.BASE_TYPE_USAGE,
                        full_name,
                    )

    def has_parameters(self, annotation: ast.Subscript) -> bool:
        """Determine if a Subscript annotation has parameters.

        Checks whether a subscript annotation has proper parameterization.
        For example, in "Iterable[UserId]" parameterization is present,
        while in "dict" without parameters it is absent.
        """
        slice_node = annotation.slice

        if isinstance(slice_node, ast.Name):
            return not (
                slice_node.id in DISALLOWED_GENERIC_TYPES or slice_node.id in DISALLOWED_BASE_TYPES
            )

        if isinstance(slice_node, ast.Tuple):
            return True
        return True

    def get_full_attr_name(self, node: ast.Attribute) -> str:
        """Get the full attribute name from an Attribute node.

        Reconstructs the full dotted name from an attribute node.
        For example, for the node representing "module.submodule.Type",
        returns the string "module.submodule.Type".
        """
        attr_names = []

        while isinstance(node, ast.Attribute):
            attr_names.append(node.attr)
            node = node.value

        if isinstance(node, ast.Name):
            attr_names.append(node.id)

        return ".".join(reversed(attr_names))


def scan_file(filepath: str) -> List[Problem]:
    """Scan a single file for domain type violations.

    Opens the file, parses it into an AST, and runs the linter on it.
    Prints any problems found to stderr.

    Args:
        filepath: Path to the file to scan

    Returns:
        list[Problem]: List of problems found in the file
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
        source_lines = source.splitlines()

    tree = ast.parse(source, filepath)

    linter = Linter(source_lines=source_lines, filepath=filepath)
    linter.visit(tree)

    if linter.problems:
        print(f"{filepath}:", file=sys.stderr)

        for problem in linter.problems:
            print(problem, file=sys.stderr)

        return linter.problems

    else:
        return []


def scan_path(path: str) -> List[Tuple[Path, List[Problem]]]:
    """Scan a file or directory for domain type violations.

    If the path is a file, scans just that file.
    If the path is a directory, recursively scans all Python files in it.

    Args:
        path: Path to the file or directory to scan

    Returns:
        List[Tuple[Path, List[Problem]]]: List of tuples containing the path and the problems found

    Raises:
        ValueError: If the path does not exist
    """
    path_obj = Path(path)
    problems: List[Tuple[Path, List[Problem]]] = []

    if path_obj.is_file():
        return [(path_obj, scan_file(path))]

    elif path_obj.is_dir():
        for path in path_obj.rglob("*.py"):
            problems.append((path_obj, scan_file(str(path))))

        return problems

    else:
        raise ValueError(f"The path does not exist {path}")
