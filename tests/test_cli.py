import sys
from pathlib import Path
from unittest.mock import patch

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

        scan_path.assert_called_once_with(test_path)
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
