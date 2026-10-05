import ast
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union

from domain_types_linter.config import Config, find_config
from domain_types_linter.types_and_codes import (
    ALIAS_TYPE_CODE,
    TYPE_CODES,
    DISALLOWED_BASE_TYPES,
    DISALLOWED_GENERIC_TYPES,
    ALLOWED_GENERIC_TYPES,
)

# "# dt: ignore" on the line of a "def" or "class" skips the whole function or class.
IGNORE_DEFINITION_RE = re.compile(r"#\s*dt:\s*ignore\b", re.IGNORECASE)

# A noqa comment without codes or with codes (noqa: DT003,DT004) skips problems on the line.
# Used in the CLI only, flake8 handles noqa comments itself.
NOQA_RE = re.compile(
    r"#\s*noqa(?::[\s]?(?P<codes>[A-Z]+[0-9]+(?:[,\s]+[A-Z]+[0-9]+)*))?", re.IGNORECASE
)

FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


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
        target_name: Name of the annotated parameter, attribute or variable
            (empty for return annotations)
        site: Position (line, column) of the whole annotation the problem belongs to
        note: Additional explanation appended to the message
    """

    line_number: int
    problem_type: ProblemType
    type_name: str
    filepath: str
    object_type: str = ""
    code_line: str = ""
    target_name: str = ""
    site: Tuple[int, int] = (0, 0)
    note: str = ""

    def __str__(self) -> str:
        code = self.get_problem_code()
        message = self.get_problem_message()
        line_info = f"{self.filepath}:{self.line_number}: {code} {message}"
        return line_info

    def get_problem_code(self) -> str:
        if self.problem_type == ProblemType.ALIAS_USAGE:
            return ALIAS_TYPE_CODE

        # For "module.Type" the code is determined by "Type".
        type_lower = self.type_name.rsplit(".", 1)[-1].lower()

        return TYPE_CODES.get(type_lower, "DT999")

    def get_problem_message(self) -> str:
        message = self._get_base_message()
        if self.note:
            return f"{message} ({self.note})"
        return message

    def _get_base_message(self) -> str:
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
        aliases: User-defined aliases for universal types mapped to the aliased type
        source_lines: Source code lines of the file being analyzed
        filepath: Path to the file being analyzed
        config: Linter settings
    """

    def __init__(
        self,
        source_lines: Optional[List[str]] = None,
        filepath: str = "",
        config: Optional[Config] = None,
    ):
        """
        Args:
            source_lines: List of source code lines (optional)
            filepath: Path to the file being analyzed (optional)
            config: Linter settings (optional, strict defaults are used if not given)
        """
        self.problems: List[Problem] = []
        # User-defined aliases (e.g., alias_str -> str derived from alias_str = str)
        self.aliases: Dict[str, str] = {}
        self.source_lines: List[str] = source_lines if source_lines is not None else []
        self.filepath: str = filepath
        self.config: Config = config if config is not None else Config()
        # Kinds of enclosing definitions: "function" or "class".
        self._scopes: List[str] = []
        # Name and position of the annotation being checked.
        self._target_name: str = ""
        self._site: Tuple[int, int] = (0, 0)

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
            target_name=self._target_name,
            site=self._site,
        )
        self.problems.append(problem)

    def is_ignored_definition(self, node: Union[FunctionNode, ast.ClassDef]) -> bool:
        """Determine if a function or class must be skipped entirely, together with its body."""
        if self.source_lines and 0 < node.lineno <= len(self.source_lines):
            if IGNORE_DEFINITION_RE.search(self.source_lines[node.lineno - 1]):
                return True

        if not self.config.check_private and is_private_name(node.name):
            return True

        if not self.config.check_nested and "function" in self._scopes:
            return True

        return False

    def check_target_annotation(self, annotation: ast.expr, target_name: str) -> None:
        """Check the annotation of a parameter, attribute, variable or return value."""
        self._target_name = target_name.lstrip("_")
        self._site = (annotation.lineno, annotation.col_offset)
        try:
            self.check_annotation(annotation)
        finally:
            self._target_name = ""
            self._site = (0, 0)

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
                    self.aliases[target.id] = node.value.id
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit an annotated assignment node.

        Checks the type annotation in the assignment.
        Local variables are skipped if check_local_variables is disabled.
        """
        is_local = bool(self._scopes) and self._scopes[-1] == "function"

        if node.annotation and (self.config.check_local_variables or not is_local):
            self.check_target_annotation(node.annotation, get_target_name(node.target))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition node.

        Skips the class entirely if it is ignored by settings or by a "# dt: ignore" comment.
        """
        if self.is_ignored_definition(node):
            return

        self._scopes.append("class")
        try:
            self.generic_visit(node)
        finally:
            self._scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_function(node)

    def visit_function(self, node: FunctionNode) -> None:
        """Visit a function or async function definition node.

        Checks the return type annotation and argument type annotations.
        Skips the function entirely if it is ignored by settings or by a "# dt: ignore" comment.
        """
        if self.is_ignored_definition(node):
            return

        if node.returns:
            self.check_target_annotation(node.returns, "")
        for arg in node.args.args:
            if arg.annotation:
                self.check_target_annotation(arg.annotation, arg.arg)

        self._scopes.append("function")
        try:
            self.generic_visit(node)
        finally:
            self._scopes.pop()

    def check_annotation(self, annotation: ast.expr) -> None:
        """Check a type annotation for domain type violations.

        Recursively checks type annotations for violations of domain type rules.
        """
        if isinstance(annotation, ast.Name):
            if annotation.id in self.config.allowed_types:
                return

            if annotation.id in self.aliases:
                if self.aliases[annotation.id] in self.config.allowed_types:
                    return

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

                if type_name in self.config.allowed_types:
                    self.check_annotation(inner_annotation)

                elif type_name in DISALLOWED_GENERIC_TYPES:
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

            # We check if the attribute is the prohibited basic type, e.g. decimal.Decimal.
            if (
                annotation.attr in DISALLOWED_BASE_TYPES
                and annotation.attr not in self.config.allowed_types
            ):
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
            if slice_node.id in self.config.allowed_types:
                return True

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


def is_private_name(name: str) -> bool:
    """Determine if a name is private: starts with "_" and is not a dunder name like __init__."""
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def get_target_name(target: ast.expr) -> str:
    """Get the name of an annotated assignment target: "x" for "x: int", "y" for "self.y: int"."""
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return ""


def is_noqa(problem: Problem) -> bool:
    """Determine if a problem is suppressed by a "# noqa" comment on its line."""
    match = NOQA_RE.search(problem.code_line)
    if not match:
        return False

    codes = match.group("codes")
    if not codes:
        return True

    return problem.get_problem_code() in {c.upper() for c in re.split(r"[,\s]+", codes) if c}


def lint_file(filepath: str, config: Optional[Config] = None) -> List[Problem]:
    """Lint a single file without printing anything.

    Problems suppressed by "# noqa" comments are not returned.

    Args:
        filepath: Path to the file to lint
        config: Linter settings (optional)

    Returns:
        list[Problem]: List of problems found in the file
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
        source_lines = source.splitlines()

    tree = ast.parse(source, filepath)

    linter = Linter(source_lines=source_lines, filepath=filepath, config=config)
    linter.visit(tree)

    return [p for p in linter.problems if not is_noqa(p)]


def filter_frequent(
    problems: List[Problem], min_occurrences: int, min_modules: int
) -> List[Problem]:
    """Keep only problems of names that are annotated with universal types often.

    Problems are grouped by the name of the annotated parameter, attribute or variable.
    A group is kept if the name is annotated with universal types at least min_occurrences
    times in at least min_modules different files. Return annotations have no name and are dropped.
    """
    groups: Dict[str, List[Problem]] = defaultdict(list)
    for problem in problems:
        if problem.target_name:
            groups[problem.target_name].append(problem)

    kept = set()
    for name, group in groups.items():
        sites = {(p.filepath, p.site) for p in group}
        modules = {p.filepath for p in group}

        if len(sites) >= min_occurrences and len(modules) >= min_modules:
            for problem in group:
                problem.note = (
                    f"'{name}' is annotated with universal types {len(sites)} times "
                    f"in {len(modules)} module(s), consider a domain type"
                )
                kept.add(id(problem))

    return [p for p in problems if id(p) in kept]


def print_problems(filepath: str, problems: List[Problem]) -> None:
    """Print problems of a file to stderr."""
    if problems:
        print(f"{filepath}:", file=sys.stderr)

        for problem in problems:
            print(problem, file=sys.stderr)


def scan_file(filepath: str, config: Optional[Config] = None) -> List[Problem]:
    """Scan a single file for domain type violations.

    Opens the file, parses it into an AST, and runs the linter on it.
    Prints any problems found to stderr.

    Args:
        filepath: Path to the file to scan
        config: Linter settings (optional)

    Returns:
        list[Problem]: List of problems found in the file
    """
    problems = lint_file(filepath, config)
    print_problems(filepath, problems)
    return problems


def scan_path(path: str, config: Optional[Config] = None) -> List[Tuple[Path, List[Problem]]]:
    """Scan a file or directory for domain type violations.

    If the path is a file, scans just that file.
    If the path is a directory, recursively scans all Python files in it.
    Files are filtered by the include/exclude settings.
    In frequent mode only names that are annotated with universal types often are reported.
    Prints any problems found to stderr.

    Args:
        path: Path to the file or directory to scan
        config: Linter settings (optional, searched in pyproject.toml if not given)

    Returns:
        List[Tuple[Path, List[Problem]]]: List of tuples containing the path and the problems found

    Raises:
        ValueError: If the path does not exist
    """
    path_obj = Path(path)
    if config is None:
        config = find_config(path_obj)

    if path_obj.is_file():
        file_paths = [path_obj]

    elif path_obj.is_dir():
        file_paths = sorted(path_obj.rglob("*.py"))

    else:
        raise ValueError(f"The path does not exist {path}")

    results = [
        (file_path, lint_file(str(file_path), config))
        for file_path in file_paths
        if config.is_file_included(str(file_path))
    ]

    if config.frequent:
        all_problems = [p for _, problems in results for p in problems]
        frequent = {
            id(p) for p in filter_frequent(all_problems, config.min_occurrences, config.min_modules)
        }
        results = [
            (file_path, [p for p in problems if id(p) in frequent])
            for file_path, problems in results
        ]

    for file_path, problems in results:
        print_problems(str(file_path), problems)

    return results
