import ast
import sys

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
}

# Допустимые обобщённые типы (например, Callable, Type и т.д.)
ALLOWED_GENERIC_TYPES = {"Callable", "Awaitable", "Type"}


class Linter(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        # Множество алиасов, созданных пользователем (например, alias_str, полученные из alias_str = str)
        self.aliases = set()

    def record_error(self, node: ast.AST, message: str):
        lineno = getattr(node, "lineno", "неизвестно")
        self.errors.append(f"Строка {lineno}: {message}")

    def visit_Module(self, node: ast.Module):
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """
        Если обнаружено присваивание вида:
            alias_str = str
        то оно разрешается, и имя алиаса сохраняется в self.aliases.
        """
        if isinstance(node.value, ast.Name) and node.value.id in DISALLOWED_BASE_TYPES:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.aliases.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if node.annotation:
            self.check_annotation(node.annotation)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.returns:
            self.check_annotation(node.returns)
        for arg in node.args.args:
            if arg.annotation:
                self.check_annotation(arg.annotation)
        self.generic_visit(node)

    def check_annotation(self, annotation: ast.expr):
        if isinstance(annotation, ast.Name):
            if annotation.id in self.aliases:
                self.record_error(
                    annotation,
                    f"Использование алиаса '{annotation.id}' в аннотации недопустимо.",
                )
            elif annotation.id in DISALLOWED_BASE_TYPES:
                self.record_error(
                    annotation,
                    f"Использование универсального типа '{annotation.id}' недопустимо.",
                )
            elif annotation.id in DISALLOWED_GENERIC_TYPES:
                self.record_error(
                    annotation,
                    f"Использование универсального контейнера '{annotation.id}' без параметров недопустимо.",
                )
        elif isinstance(annotation, ast.Subscript):
            outer_type = annotation.value
            inner_annotation = annotation.slice

            if isinstance(outer_type, ast.Name):
                type_name = outer_type.id
                if type_name in DISALLOWED_GENERIC_TYPES:
                    if not self.has_parameters(annotation):
                        self.record_error(
                            outer_type,
                            f"Использование универсального контейнера '{type_name}' без параметров недопустимо.",
                        )
                    self.check_annotation(inner_annotation)
                elif type_name in ALLOWED_GENERIC_TYPES:
                    self.check_annotation(inner_annotation)
                else:
                    self.check_annotation(inner_annotation)
            else:
                self.check_annotation(outer_type)
                self.check_annotation(inner_annotation)
        # Проверка объединения типов через оператор "|" (Python 3.10+)
        elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            self.check_annotation(annotation.left)
            self.check_annotation(annotation.right)
        # Если аннотация – кортеж, например: Tuple[int, str, ...]
        elif isinstance(annotation, ast.Tuple):
            for elt in annotation.elts:
                self.check_annotation(elt)
        # Обработка вызовов (например, NewType("UserId", int))
        elif isinstance(annotation, ast.Call):
            for arg in annotation.args:
                self.check_annotation(arg)
        # Если аннотация представлена через Attribute, например: module.Type
        elif isinstance(annotation, ast.Attribute):
            full_name = self.get_full_attr_name(annotation)
            # Проверяем, если атрибут заканчивается на запрещённый базовый тип.
            for disallowed in DISALLOWED_BASE_TYPES:
                if full_name.endswith(disallowed):
                    self.record_error(
                        annotation,
                        f"Использование универсального типа '{full_name}' недопустимо.",
                    )

    def has_parameters(self, annotation: ast.Subscript) -> bool:
        """
        Определяет, что у Subscript-аннотации присутствует параметризация.
        Например: в "Iterable[UserId]" параметризация присутствует, в "dict" без параметров – отсутствует.
        """
        slice_node = annotation.slice
        if isinstance(slice_node, ast.Name):
            return not (
                slice_node.id in DISALLOWED_GENERIC_TYPES
                or slice_node.id in DISALLOWED_BASE_TYPES
            )
        if isinstance(slice_node, ast.Tuple):
            return True
        return True

    def get_full_attr_name(self, node: ast.Attribute):
        attr_names = []
        while isinstance(node, ast.Attribute):
            attr_names.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            attr_names.append(node.id)
        return ".".join(reversed(attr_names))


def main():
    path = "/domain_types_linter/linter_types_examples.py"

    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"Ошибка при открытии файла: {e}")
        sys.exit(1)

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        print(f"Синтаксическая ошибка в файле: {e}")
        sys.exit(1)

    linter = Linter()
    linter.visit(tree)
    if linter.errors:
        print("Найдены ошибки:")
        for error in linter.errors:
            print("  -", error)
        sys.exit(1)
    else:
        print("Проверка пройдена успешно!")


if __name__ == "__main__":
    main()
