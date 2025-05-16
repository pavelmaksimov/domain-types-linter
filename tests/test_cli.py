import sys
from unittest.mock import patch

import pytest

from domain_types_linter.cli import main


def test_cli_passes_path_to_linter():
    test_path = "test_path"

    with patch("domain_types_linter.cli.scan_path") as scan_path:
        with patch.object(sys, "argv", ["dt-linter", test_path]):
            with pytest.raises(SystemExit) as excinfo:
                main()

        scan_path.assert_called_once_with(test_path)
        assert excinfo.value.code == 1


def test_cli_exits_without_arguments():
    with patch.object(sys, "argv", ["dt-linter"]):
        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code != 0
