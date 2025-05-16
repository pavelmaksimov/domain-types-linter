from decimal import Decimal
from typing import *

UserId = NewType("UserId", int)

alias_str = str
typing_type_alias_str: TypeAlias = str


class DomainDataType:
    ...


# Examples of universal types that should be found by a linter:
def disallowed_types(
    my_str: str,
    my_alias_str: alias_str,
    typing_type_alias_str: typing_type_alias_str,
    my_int: int,
    my_float: float,
    my_complex: complex,
    my_bytes: bytes,
    my_bytearray: bytearray,
    my_any: Any,
    my_anystr: AnyStr,
    my_decimal: Decimal,
    my_dict_minitype_int: dict[DomainDataType, int],
    my_dict_minitype_list: dict[DomainDataType, List[Union[int, DomainDataType]]],
    my_dict_str_dict: dict[str, dict[Union[int, str], int]],
    my_dict_alias_str: dict[alias_str],
    my_list_str: list[str],
    my_list_list: List[List[Union[int, str]]],
    my_set_int_lower: set[int],
    my_frozenset_int_lower: frozenset[int],
    my_type_union: Type[Union[int, str]],
    my_iterable_int: Iterable[int],
    my_async_iterable_int: AsyncIterable[int],
    my_async_generator_int: AsyncGenerator[int, None],
    my_iterator_int: Iterator[int],
    my_container_int: Container[int],
    my_mapping_str_int: Mapping[str, int],
    my_mutable_mapping_str_int: MutableMapping[str, int],
    my_mutable_sequence_int: MutableSequence[int],
    my_sequence_int: Sequence[int],
    my_collection_int: Collection[int],
    my_reversible_int: Reversible[int],
    my_dict_str_int: Dict[str, int],
    my_list_int: List[int],
    my_list_list_int: List[List[int]],
    my_list_list_union: List[List[Union[int, str]]],
    my_set_int: Set[int],
    my_set_set_int: Set[Set[int]],
    my_frozenset_int: FrozenSet[int],
    my_deque_int: Deque[int],
    my_defaultdict_str_int: DefaultDict[str, int],
    my_chainmap_str_int: ChainMap[str, int],
    my_generator_int: Generator[int, None, None],
    my_optional_int: Optional[int],
    my_tuple_int: Tuple[int, ...],
    my_union_int_str: Union[int, str],
    my_annotated_int: Annotated[int, "meta"],
    # Types of collections, containers and other types that should be found by a linter because they may contain
    # universal types.
    my_dict: dict,
    my_set: set,
    my_tuple: tuple,
    my_list: list,
    my_frozenset: frozenset,
    my_iterable: Iterable,
    my_iterator: Iterator,
    my_async_iterator: AsyncIterator,
    my_async_generator: AsyncGenerator,
    my_async_iterable: AsyncIterable,
    my_container: Container,
    my_mapping: Mapping,
    my_mutable_mapping: MutableMapping,
    my_mutable_sequence: MutableSequence,
    my_sequence: Sequence,
    my_collection: Collection,
    my_reversible: Reversible,
    my_dict_simple: Dict,
    my_list_simple: List,
    my_set_simple: Set,
    my_frozenset_simple: FrozenSet,
    my_deque: Deque,
    my_defaultdict: DefaultDict,
    my_chainmap: ChainMap,
    my_generator: Generator,
    my_optional: Optional,
    my_tuple_simple: Tuple,
    my_type: type,
    my_type_object: Type,
):
    ...


# Types for classes that may contain universal types should be found by a linter:
class DomainClass:
    my_classvar_int: ClassVar[int]
    my_final: Final = 0
    my_final_int: Final[int] = 3


# Examples that should not be found by a linter:
def allowed_types(
    my_bool: bool,
    my_bool_none: bool | None,
    my_none: None,
    my_userid: UserId,
    my_minitype: DomainDataType,
    my_callable: Callable,
    my_callable_func: Callable[[], None],
    # etc. Examples are not given with all permitted types.,
    # Types of containers and collections that are clarified by domain types are allowed:,
    my_iterable_userid: Iterable[UserId],
    my_async_iterable_userid: AsyncIterable[UserId],
    my_async_generator_userid: AsyncGenerator[UserId, None],
    my_iterator_userid: Iterator[UserId],
    my_async_iterator_userid: AsyncIterator[UserId],
    my_container_userid: Container[UserId],
    my_mapping_userid_minitype: Mapping[UserId, DomainDataType],
    my_dict_userid_minitype: Dict[UserId, DomainDataType],
    my_list_list_union: List[List[Union[UserId, DomainDataType]]],
    my_set_userid: Set[UserId],
    my_tuple_userid: Tuple[UserId, ...],
    my_frozenset_userid: FrozenSet[UserId],
    my_dict_userid_minitype_lower: dict[UserId, DomainDataType],
    my_list_list_union_lower: list[list[UserId | DomainDataType]],
    my_set_userid_lower: set[UserId],
    my_tuple_userid_lower: tuple[UserId, ...],
    my_frozenset_userid_lower: frozenset[UserId],
    my_optional_userid: Optional[UserId],
    # etc. Examples are not given with all types of containers.
):
    ...
