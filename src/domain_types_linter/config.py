import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Name of the section in pyproject.toml: [tool.domain-types-linter]
CONFIG_SECTION = "domain-types-linter"


@dataclass
class Config:
    """Linter settings, usually read from the [tool.domain-types-linter] section of pyproject.toml.

    Attributes:
        root: Directory that include/exclude patterns are relative to
            (the directory containing pyproject.toml)
        include: Path patterns of files to check. If empty, all files are checked
        exclude: Path patterns of files to skip
        allowed_types: Type names that are allowed everywhere (e.g. "int", "dict")
        check_private: Check functions, methods and classes whose names start with "_"
        check_nested: Check functions and classes defined inside other functions
        check_local_variables: Check annotations of local variables inside functions
        frequent: Report only names that are annotated with universal types often (CLI only)
        min_occurrences: Minimum number of annotations of a name to report it in frequent mode
        min_modules: Minimum number of modules a name must appear in to report it in frequent mode
    """

    root: Path = field(default_factory=Path.cwd)
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    allowed_types: Set[str] = field(default_factory=set)
    check_private: bool = True
    check_nested: bool = True
    check_local_variables: bool = True
    frequent: bool = False
    min_occurrences: int = 3
    min_modules: int = 1

    @classmethod
    def from_dict(cls, data: Dict[str, Any], root: Path) -> "Config":
        """Create a config from the contents of the [tool.domain-types-linter] section.

        Raises:
            ValueError: If the section contains unknown keys or values of the wrong type
        """
        unknown = set(data) - set(_KEYS)
        if unknown:
            raise ValueError(f"Unknown {CONFIG_SECTION} settings: {', '.join(sorted(unknown))}")

        kwargs: Dict[str, Any] = {"root": root}
        for key, value in data.items():
            attr, expected_type = _KEYS[key]
            if expected_type is list:
                if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                    raise ValueError(f"{CONFIG_SECTION} setting '{key}' must be a list of strings")
                kwargs[attr] = set(value) if attr == "allowed_types" else list(value)
            elif not isinstance(value, expected_type) or (
                expected_type is int and isinstance(value, bool)
            ):
                raise ValueError(
                    f"{CONFIG_SECTION} setting '{key}' must be of type {expected_type.__name__}"
                )
            else:
                kwargs[attr] = value

        return cls(**kwargs)

    def is_file_included(self, filepath: str) -> bool:
        """Check the include/exclude patterns for a file.

        Patterns are matched against the path relative to the config root.
        A pattern matches if it is equal to the path or to one of its parent directories,
        or if it matches as a glob (where "*" also matches "/").
        """
        if not self.include and not self.exclude:
            return True

        relative = self._relative_path(filepath)

        if self.include and not any(_match(relative, p) for p in self.include):
            return False

        return not any(_match(relative, p) for p in self.exclude)

    def _relative_path(self, filepath: str) -> str:
        path = Path(filepath).resolve()
        try:
            return path.relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()


# Mapping of pyproject.toml keys to Config attributes and their expected types.
_KEYS = {
    "include": ("include", list),
    "exclude": ("exclude", list),
    "allowed-types": ("allowed_types", list),
    "check-private": ("check_private", bool),
    "check-nested": ("check_nested", bool),
    "check-local-variables": ("check_local_variables", bool),
    "frequent": ("frequent", bool),
    "min-occurrences": ("min_occurrences", int),
    "min-modules": ("min_modules", int),
}


def _match(relative_path: str, pattern: str) -> bool:
    pattern = pattern.strip("/")
    if pattern.startswith("./"):
        pattern = pattern[2:]
    return (
        relative_path == pattern
        or relative_path.startswith(pattern + "/")
        or fnmatch(relative_path, pattern)
    )


def _read_section(pyproject: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Failed to parse {pyproject}: {e}") from e

    return data.get("tool", {}).get(CONFIG_SECTION)


def load_config(pyproject: Path) -> Config:
    """Load the config from the given pyproject.toml file.

    If the file has no [tool.domain-types-linter] section, the default config is returned.
    """
    section = _read_section(pyproject)
    return Config.from_dict(section or {}, root=pyproject.resolve().parent)


def find_config(start: Path) -> Config:
    """Find the closest pyproject.toml with a [tool.domain-types-linter] section.

    The search goes from the start path up to the file system root.
    If nothing is found, the default config is returned.
    """
    start = start.resolve()
    if not start.is_dir():
        start = start.parent

    for directory in (start, *start.parents):
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            section = _read_section(pyproject)
            if section is not None:
                return Config.from_dict(section, root=directory)

    return Config()
