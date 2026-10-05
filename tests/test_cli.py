import sys
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

from domain_types_linter.cli import main
from domain_types_linter.main import Problem, ProblemType


def _result_with_problems():
    problem = Problem(
        line_number=1,
        problem_type=ProblemType.BASE_TYPE_USAGE,
        type_name="str",
        filepath="test_path",
    )
    return [(Path("test_path"), [problem])]


def _clean_result():
    return [(Path("test_path"), [])]


def test_cli_passes_path_to_linter():
    """Test that the CLI correctly passes the provided path to the linter function."""
    test_path = "test_path"

    with patch("domain_types_linter.cli.scan_path") as scan_path:
        scan_path.return_value = _result_with_problems()
        with patch.object(sys, "argv", ["dt-linter", test_path]):
            with pytest.raises(SystemExit) as excinfo:
                main()

        scan_path.assert_called_once_with(test_path, ANY)
        assert excinfo.value.code == 1


def test_cli_exits_zero_when_no_problems(capsys):
    """Test that the CLI exits with code 0 on clean files."""
    with patch("domain_types_linter.cli.scan_path") as scan_path:
        scan_path.return_value = _clean_result()
        with patch.object(sys, "argv", ["dt-linter", "test_path"]):
            main()

        captured = capsys.readouterr()
        assert "All checks have been successful!" in captured.out


def test_cli_exits_without_arguments():
    """Test that the CLI exits with an error code when no arguments are provided."""
    with patch.object(sys, "argv", ["dt-linter"]):
        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code != 0


def test_cli_frequent_options_override_config():
    """Test that frequent mode options from the command line override the config."""
    with patch("domain_types_linter.cli.scan_path") as scan_path:
        scan_path.return_value = _clean_result()
        argv = ["dt-linter", "test_path", "--frequent", "--min-occurrences", "5"]
        with patch.object(sys, "argv", argv):
            main()

        config = scan_path.call_args.args[1]
        assert config.frequent
        assert config.min_occurrences == 5
        assert config.min_modules == 1


def test_cli_exits_with_config_error(tmp_path):
    """Test that the CLI exits with code 2 if the config is invalid."""
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text("[tool.domain-types-linter]\nunknown = 1\n")

    with patch.object(sys, "argv", ["dt-linter", str(tmp_path), "--config", str(config_path)]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 2
