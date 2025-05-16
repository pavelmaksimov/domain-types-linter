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

The linter will scan the specified file or directory recursively and report any domain type violations. 
It will exit with code 1 if problems are found.

### Flake8 Plugin
If you have installed the linter with Flake8 support, you can use it as a Flake8 plugin:

```bash
flake8 path/to/file_or_directory
```

The domain type violations will be reported along with other Flake8 errors.

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
