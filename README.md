# Domain Types Linter

A static code analyzer that enforces the use of domain-specific types in business logic code instead of universal types.

## Description

Domain Types Linter is a tool that helps maintain better code organization and type safety by ensuring 
that your business logic layer uses only explicit business logic objects, not universal types. 
It analyzes Python type annotations and reports violations of domain type rules.

The linter detects three types of problems:
- Using an alias for a universal type (e.g., `alias_str = str`)
- Using a universal base type directly (e.g., `str`, `int`)
- Using a generic type without domain-specific parameters (e.g., `List` without proper domain types)

## Installation

### Requirements
- Python 3.10 or higher

### Basic Installation
```bash
pip install domain-types-linter
```

### Installation with Flake8 Support
```bash
pip install domain-types-linter[flake8]
```

## Usage

### Command Line Interface
You can run the linter directly from the command line:

```bash
dt-linter path/to/file_or_directory
```

The linter will scan the specified file or directory recursively and report any domain type violations
in annotations of functions (including `async` functions), class attributes and variables.
It will exit with code 1 if problems are found.

### Flake8 Plugin
If you have installed the linter with Flake8 support, you can use it as a Flake8 plugin:

```bash
flake8 path/to/file_or_directory
```

The domain type violations will be reported along with other Flake8 errors.

## Configuration

Keeping domain types for every function is expensive. A helper that is used in one module
rarely needs its own domain types. The rules can be relaxed in the `[tool.domain-types-linter]`
section of `pyproject.toml`. Both the CLI and the Flake8 plugin use the closest `pyproject.toml`
with this section. By default, all checks are enabled.

```toml
[tool.domain-types-linter]
# Check only these paths (relative to the directory of pyproject.toml).
include = ["src/app/domain", "src/app/services"]
# Skip these paths. "*" also matches "/", e.g. "*/migrations/*".
exclude = ["src/app/services/legacy", "*/migrations/*"]
# Types that are allowed everywhere.
allowed-types = ["bool", "Any"]
# Check functions, methods and classes whose names start with "_" (except dunder methods like __init__).
check-private = false
# Check functions and classes defined inside other functions.
check-nested = false
# Check annotations of local variables inside functions (class and module attributes are always checked).
check-local-variables = false
# Frequent mode, see below (CLI only).
frequent = false
min-occurrences = 3
min-modules = 1
```

A pattern in `include` and `exclude` matches a file if it is the file path, one of its parent
directories, or a glob that matches the path.

Use `--config path/to/pyproject.toml` to point the CLI to a specific config file.

### Frequent mode

A domain type is worth creating for a concept that is used in many places.
In frequent mode the linter reports only names of parameters, attributes and variables
that are annotated with universal types at least `min-occurrences` times
in at least `min-modules` modules:

```bash
dt-linter src --frequent --min-occurrences 3 --min-modules 2
```

```
src/users.py:4: DT004 forbidden to use universal type 'int' ('user_id' is annotated with universal types 14 times in 6 module(s), consider a domain type)
```

Names are compared without leading underscores, so `_user_id` and `user_id` are counted together.
Return annotations have no name and are not reported in this mode.
Frequent mode needs the whole project, so it is available in the CLI only and is ignored by the Flake8 plugin.

### Suppressing problems

- `# noqa` or `# noqa: DT004` at the end of a line suppresses problems on that line
  (in the CLI; Flake8 handles `noqa` comments itself).
- `# dt: ignore` on the line of a `def` or `class` skips the whole function or class,
  including its body. Works in the CLI and in the Flake8 plugin.

```python
def parse_row(row: dict) -> tuple:  # dt: ignore
    ...

def get_user(user_id: int, raw: str): ...  # noqa: DT003
```

## Examples

### Disallowed Types

The following types are not allowed in business logic code:

```python
# Universal base types
def disallowed_base_types(
    my_str: str,
    my_int: int,
    my_float: float,
    my_complex: complex,
    my_bytes: bytes,
    my_bytearray: bytearray,
    my_any: Any,
    my_decimal: Decimal,
):
    ...

# Aliases of universal types
alias_str = str
typing_type_alias_str: TypeAlias = str

def disallowed_aliases(
    my_alias_str: alias_str,
    my_typing_alias: typing_type_alias_str,
):
    ...

# Generic types with universal type parameters
def disallowed_generic_types(
    my_list_str: list[str],
    my_dict_str_int: Dict[str, int],
    my_set_int: Set[int],
    my_tuple_int: Tuple[int, ...],
    my_optional_int: Optional[int],
):
    ...

# Generic types without parameters
def disallowed_generic_types_without_params(
    my_list: list,
    my_dict: dict,
    my_set: set,
    my_tuple: tuple,
    my_iterable: Iterable,
):
    ...
```

### Allowed Types

The following types are allowed in business logic code:

```python
# Domain-specific types
UserId = NewType("UserId", int)

class DomainDataType:
    ...

# Using domain-specific types
def allowed_types(
    my_bool: bool,  # bool is allowed
    my_none: None,  # None is allowed
    my_callable: Callable,  # Callable is allowed without parameters
    my_userid: UserId,  # Domain-specific type
    my_domain_type: DomainDataType,  # Domain-specific class
):
    ...

# Generic types with domain-specific parameters
def allowed_generic_types(
    my_list_userid: List[UserId],
    my_dict_userid_domain: Dict[UserId, DomainDataType],
    my_set_userid: Set[UserId],
    my_tuple_userid: Tuple[UserId, ...],
    my_optional_userid: Optional[UserId],
):
    ...
```

## Problem Codes

The linter uses the following problem codes:

- `DT001`: Using an alias for a universal type
- `DT003` - `DT011`: Using universal base types (str, int, float, etc.)
- `DT100` - `DT125`: Using parameterized types without domain-specific parameters

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
