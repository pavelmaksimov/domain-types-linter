import ast
import tempfile
from pathlib import Path

from domain_types_linter.flake8_plugin import DomainTypesLinter


def test_plugin_initialization():
    """Test that the plugin can be initialized with the required parameters."""
    tree = ast.parse("")
    plugin = DomainTypesLinter(tree=tree, filename="test.py", lines=[])
    assert plugin.tree == tree
    assert plugin.filename == "test.py"
    assert plugin.source_lines == []


def test_plugin_run_with_no_errors():
    """Test that the plugin returns no errors for valid code."""
    code = """
def valid_function(domain_user_id: UserId) -> UserName:
    return UserName("John")
"""
    tree = ast.parse(code)
    plugin = DomainTypesLinter(tree=tree, filename="test.py", lines=code.splitlines())
    errors = list(plugin.run())
    assert len(errors) == 0


def test_plugin_run_with_errors():
    """Test that the plugin returns errors for invalid code."""
    code = """
def invalid_function(user_id: str) -> str:
    return "John"
"""
    tree = ast.parse(code)
    plugin = DomainTypesLinter(tree=tree, filename="test.py", lines=code.splitlines())
    errors = list(plugin.run())
    assert len(errors) > 0
    assert errors[0][0] == 2  # Line number
    assert "DT003" in errors[0][2]  # Error code for str


def test_plugin_integration_with_temp_file():
    """Test the plugin with a temporary file to ensure it works with real files."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        f.write(b"""
def invalid_function(user_id: int) -> int:
    return 42
""")
        filename = f.name

    try:
        tree = ast.parse(Path(filename).read_text())
        plugin = DomainTypesLinter(tree=tree, filename=filename)
        errors = list(plugin.run())
        assert len(errors) > 0
        assert errors[0][0] == 2  # Line number
        assert "DT004" in errors[0][2]  # Error code for int
    finally:
        Path(filename).unlink()
