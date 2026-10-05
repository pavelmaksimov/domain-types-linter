import ast
import textwrap
from pathlib import Path

import pytest

from domain_types_linter.config import Config, find_config, load_config
from domain_types_linter.flake8_plugin import DomainTypesLinter, _config_cache
from domain_types_linter.main import Linter, lint_file, scan_path


def lint(code: str, config: Config = None):
    code = textwrap.dedent(code)
    linter = Linter(code.splitlines(), "test.py", config)
    linter.visit(ast.parse(code))
    return [(p.line_number, p.get_problem_code()) for p in linter.problems]


def write(path: Path, code: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(code), encoding="utf-8")
    return path


def test_async_functions_are_checked():
    """Test that parameters and return types of async functions are checked."""
    code = """
    async def load(user_id: int) -> str:
        ...
    """
    assert lint(code) == [(2, "DT003"), (2, "DT004")]


def test_strict_by_default():
    """Test that private, nested functions and local variables are checked by default."""
    code = """
    def _private(a: int): ...

    def outer():
        x: str = ""
        def inner(b: int): ...
    """
    assert lint(code) == [(2, "DT004"), (5, "DT003"), (6, "DT004")]


def test_check_private_disabled():
    """Test that private functions, methods and classes are skipped together with their bodies."""
    code = """
    def _helper(a: int) -> int: ...

    async def _async_helper(a: int): ...

    class Service:
        def __init__(self, a: int): ...
        def _method(self, a: int): ...
        def __mangled(self, a: int): ...

    class _Private:
        field: int
    """
    assert lint(code, Config(check_private=False)) == [(7, "DT004")]


def test_check_nested_disabled():
    """Test that functions and classes inside functions are skipped."""
    code = """
    def outer(a: int):
        def inner(b: int): ...
        class Local:
            field: int
    """
    assert lint(code, Config(check_nested=False)) == [(2, "DT004")]


def test_check_local_variables_disabled():
    """Test that local variables are skipped, but class and module attributes are checked."""
    code = """
    module_var: int = 1

    class Entity:
        field: str

        def method(self):
            local: int = 1
            self.attr: str = ""

    def func():
        local: int = 1
    """
    assert lint(code, Config(check_local_variables=False)) == [(2, "DT004"), (5, "DT003")]


def test_allowed_types():
    """Test that allowed types are not reported, including inside generics and aliases."""
    code = """
    import decimal

    alias_int = int

    def func(
        a: int,
        b: Optional[int],
        c: dict[int, str],
        d: alias_int,
        e: decimal.Decimal,
        f: dict,
        g: str,
    ): ...
    """
    config = Config(allowed_types={"int", "dict", "Decimal"})
    assert lint(code, config) == [(9, "DT003"), (13, "DT003")]


def test_attribute_types_match_whole_name():
    """Test that module.Type is reported only for a universal type, not by name suffix."""
    code = """
    def func(a: geometry.Point, b: decimal.Decimal): ...
    """
    assert lint(code) == [(2, "DT009")]


def test_dt_ignore_comment_skips_definition():
    """Test that "# dt: ignore" on a def or class line skips the whole definition."""
    code = """
    def helper(  # dt: ignore
        a: int,
    ) -> str:
        x: int = 1

    @decorator
    async def async_helper(a: int): ...  # dt: ignore

    class Dto:  # dt: ignore
        field: int

    def checked(a: int): ...
    """
    assert lint(code) == [(13, "DT004")]


def test_noqa_in_cli(tmp_path):
    """Test that "# noqa" comments suppress problems in the CLI."""
    path = write(
        tmp_path / "module.py",
        """
        def func(
            a: int,  # noqa
            b: int,  # noqa: DT004
            c: int,  # noqa: DT003
            d: dict[str, int],  # noqa:DT003
            e: str,
        ): ...
        """,
    )
    problems = lint_file(str(path))
    assert [(p.line_number, p.get_problem_code()) for p in problems] == [
        (5, "DT004"),
        (6, "DT004"),
        (7, "DT003"),
    ]


def test_include_exclude(tmp_path):
    """Test that only included and not excluded files are checked."""
    code = "def func(a: int): ...\n"
    write(tmp_path / "app/domain/model.py", code)
    write(tmp_path / "app/domain/generated/schema.py", code)
    write(tmp_path / "app/utils.py", code)
    write(tmp_path / "scripts/run.py", code)

    config = Config(root=tmp_path, include=["app"], exclude=["*/generated/*", "app/utils.py"])
    results = scan_path(str(tmp_path), config)

    checked = {path.relative_to(tmp_path).as_posix() for path, _ in results}
    assert checked == {"app/domain/model.py"}


def test_config_from_pyproject(tmp_path):
    """Test that the config is found in the closest pyproject.toml with the section."""
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.domain-types-linter]
        include = ["src"]
        exclude = ["src/legacy"]
        allowed-types = ["int"]
        check-private = false
        check-nested = false
        check-local-variables = false
        frequent = true
        min-occurrences = 5
        min-modules = 2
        """,
    )
    write(tmp_path / "src/pkg/pyproject.toml", "[project]\nname = 'pkg'\n")

    config = find_config(tmp_path / "src/pkg")

    assert config.root == tmp_path
    assert config.include == ["src"]
    assert config.exclude == ["src/legacy"]
    assert config.allowed_types == {"int"}
    assert not config.check_private
    assert not config.check_nested
    assert not config.check_local_variables
    assert config.frequent
    assert config.min_occurrences == 5
    assert config.min_modules == 2


def test_config_defaults_without_section(tmp_path):
    """Test that the default config is used if pyproject.toml has no section."""
    path = write(tmp_path / "pyproject.toml", "[project]\nname = 'x'\n")
    assert load_config(path) == Config(root=tmp_path)


@pytest.mark.parametrize(
    "content",
    [
        "unknown-key = 1",
        "check-private = 'no'",
        "allowed-types = 'int'",
        "min-occurrences = true",
    ],
)
def test_invalid_config(tmp_path, content):
    """Test that unknown keys and values of the wrong type are rejected."""
    path = write(tmp_path / "pyproject.toml", f"[tool.domain-types-linter]\n{content}\n")
    with pytest.raises(ValueError):
        load_config(path)


def test_frequent_mode(tmp_path):
    """Test that only names annotated with universal types often enough are reported.

    "amount" is annotated twice, but in one module only, so it is not reported.
    """
    write(
        tmp_path / "users.py",
        """
        def get_user(user_id: int) -> str: ...
        def delete_user(user_id: Optional[int]): ...
        def helper(retry_count: int): ...
        """,
    )
    write(
        tmp_path / "orders.py",
        """
        class Order:
            user_id: int
            _amount: int

        def total(amount: int): ...
        """,
    )

    config = Config(root=tmp_path, frequent=True, min_occurrences=2, min_modules=2)
    results = scan_path(str(tmp_path), config)

    found = sorted(
        (path.name, p.line_number, p.target_name, p.get_problem_code())
        for path, problems in results
        for p in problems
    )
    assert found == [
        ("orders.py", 3, "user_id", "DT004"),
        ("users.py", 2, "user_id", "DT004"),
        ("users.py", 3, "user_id", "DT004"),
        ("users.py", 3, "user_id", "DT120"),
    ]

    user_id_problem = next(
        p for _, problems in results for p in problems if p.target_name == "user_id"
    )
    assert "'user_id' is annotated with universal types 3 times in 2 module(s)" in (
        user_id_problem.get_problem_message()
    )


def test_frequent_mode_min_modules(tmp_path):
    """Test that names used in fewer modules than min_modules are not reported."""
    write(
        tmp_path / "users.py",
        """
        def a(user_id: int): ...
        def b(user_id: int): ...
        def c(user_id: int): ...
        """,
    )
    config = Config(root=tmp_path, frequent=True, min_occurrences=3, min_modules=2)
    assert all(not problems for _, problems in scan_path(str(tmp_path), config))


def test_flake8_plugin_uses_pyproject_config(tmp_path):
    """Test that the flake8 plugin applies settings from pyproject.toml."""
    write(
        tmp_path / "pyproject.toml",
        """
        [tool.domain-types-linter]
        exclude = ["generated"]
        allowed-types = ["str"]
        check-private = false
        """,
    )
    code = "def func(a: int, b: str): ...\ndef _helper(a: int): ...\n"
    checked = write(tmp_path / "module.py", code)
    excluded = write(tmp_path / "generated/module.py", code)

    _config_cache.clear()
    try:
        errors = list(DomainTypesLinter(ast.parse(code), str(checked), code.splitlines(True)).run())
        assert [(line, message[:5]) for line, _, message, _ in errors] == [(1, "DT004")]

        assert list(DomainTypesLinter(ast.parse(code), str(excluded), []).run()) == []
    finally:
        _config_cache.clear()
