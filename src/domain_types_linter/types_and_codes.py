# Error code for alias usage violations
ALIAS_TYPE_CODE = "DT001"

# Mapping of type names to their corresponding error codes
TYPE_CODES = {
    # Basic types.
    # "bool": "DT002",
    "str": "DT003",
    "int": "DT004",
    "float": "DT005",
    "complex": "DT006",
    "bytes": "DT007",
    "bytearray": "DT008",
    "decimal": "DT009",
    "any": "DT010",
    "anystr": "DT011",
    # Parameterized types.
    "list": "DT100",
    "dict": "DT101",
    "set": "DT102",
    "tuple": "DT103",
    "frozenset": "DT104",
    "mapping": "DT105",
    "mutablemapping": "DT106",
    "sequence": "DT107",
    "mutablesequence": "DT108",
    "iterable": "DT109",
    "iterator": "DT110",
    "asynciterable": "DT111",
    "asynciterator": "DT112",
    "asyncgenerator": "DT113",
    "container": "DT114",
    "collection": "DT115",
    "reversible": "DT116",
    "defaultdict": "DT117",
    "chainmap": "DT118",
    "generator": "DT119",
    "optional": "DT120",
    "classvar": "DT121",
    "deque": "DT122",
    "final": "DT123",
    "annotated": "DT124",
    "type": "DT125",
}

# Set of base types that are not allowed to be used directly in domain code
DISALLOWED_BASE_TYPES = {
    "str",
    "int",
    "float",
    "complex",
    "bytes",
    "bytearray",
    "Decimal",
    "Any",
    "AnyStr",
}

# Set of generic types that are not allowed to be used without proper domain-specific parameters
DISALLOWED_GENERIC_TYPES = {
    "list",
    "List",
    "dict",
    "Dict",
    "set",
    "Set",
    "tuple",
    "Tuple",
    "frozenset",
    "FrozenSet",
    "Mapping",
    "MutableMapping",
    "Sequence",
    "MutableSequence",
    "Iterable",
    "Iterator",
    "AsyncIterable",
    "AsyncIterator",
    "AsyncGenerator",
    "Container",
    "Collection",
    "Reversible",
    "DefaultDict",
    "ChainMap",
    "Generator",
    "Optional",
    "ClassVar",
    "Deque",
    "Final",
    "Annotated",
    "Type",
    "type",
}

# Set of generic types that are allowed to be used without domain-specific parameters
ALLOWED_GENERIC_TYPES = {"Callable", "Awaitable"}
