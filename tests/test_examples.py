from pathlib import Path

from domain_types_linter.main import scan_file, scan_path
from domain_types_linter.types_and_codes import TYPE_CODES


def test_examples_file_contains_expected_problems():
    """
    Test that the examples.py file contains the expected problems when checked by the linter.
    """
    examples_path = Path(__file__).parent.parent / "example_project"

    data = scan_path(str(examples_path))
    found_codes = {p.get_problem_code() for f, problems in data for p in problems}

    skip_types = {"annotated"}

    for name, code in TYPE_CODES.items():
        if name not in skip_types:
            assert code in found_codes


def test_allowed_types_have_no_problems():
    """
    Test that the allowed_types function in examples.py has no problems.
    """
    # Create a modified version of examples.py with only the allowed_types function
    temp_file = Path(__file__).parent / "temp_allowed_types.py"

    original_examples = Path(__file__).parent.parent / "example_project/examples.py"
    with open(original_examples, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract the necessary imports and the allowed_types function
    imports = "\n".join(
        [
            "from decimal import Decimal",
            "from typing import *",
            "",
            'UserId = NewType("UserId", int)',
            "",
            "class DomainDataType:",
            "    ...",
            "",
        ]
    )

    # Find the allowed_types function in the content
    allowed_types_start = content.find("def allowed_types(")
    allowed_types_end = content.find("): ...", allowed_types_start) + 6
    allowed_types_func = content[allowed_types_start:allowed_types_end]

    # Create the temporary file with only the allowed_types function
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(imports + "\n" + allowed_types_func)

    try:
        result = scan_file(str(temp_file))

        assert result == []

    finally:
        # Clean up the temporary file
        if temp_file.exists():
            temp_file.unlink()
