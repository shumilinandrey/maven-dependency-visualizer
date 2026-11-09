"""Граф зависимостей Maven и порядок их загрузки."""

import argparse
import re
import sys
import urllib.request
import xml.etree.ElementTree as et
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

MIN_DEPTH = 0
STEP = 1
TIMEOUT = 20
ERROR = 1
NAME = r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
VERSION = r"[A-Za-z0-9_][A-Za-z0-9_.+-]*"


def validate_url(value):
    """Проверяет адрес Maven-репозитория."""
    address = urlsplit(value)
    if address.scheme not in ("http", "https") or not address.hostname:
        raise ValueError("Некорректный URL репозитория")
    if address.query or address.fragment:
        raise ValueError("URL не должен содержать query или fragment")


def validate_settings(args):
    """Проверяет имя, версию и источник данных."""
    pattern = r"[A-Z]+" if args.mode == "test" else f"{NAME}:{NAME}"
    if not re.fullmatch(pattern, args.package):
        raise ValueError("Имя: A, B, C для test; groupId:artifactId для Maven")
    if not re.fullmatch(VERSION, args.version):
        raise ValueError("Некорректная версия")
    if args.max_depth < MIN_DEPTH:
        raise ValueError("Глубина не может быть отрицательной")
    if not args.repository:
        raise ValueError("Не указан репозиторий")
    if args.mode == "url":
        validate_url(args.repository)
    elif not Path(args.repository).exists():
        raise ValueError("Указанный путь не существует")
    elif args.mode == "test" and not Path(args.repository).is_file():
        raise ValueError("Для test требуется XML-файл")


def parse_arguments():
    """Читает обязательные параметры командной строки."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--package", required=True, type=str.strip)
    parser.add_argument("-r", "--repository", required=True, type=str.strip)
    parser.add_argument(
        "-m", "--mode", required=True, choices=("url", "path", "test")
    )
    parser.add_argument("-v", "--version", required=True, type=str.strip)
    parser.add_argument("-t", "--ascii-tree", required=True, choices=("y", "n"))
    parser.add_argument("-d", "--max-depth", required=True, type=int)
    parser.add_argument("--load-order", action="store_true")
    args = parser.parse_args()
    try:
        validate_settings(args)
    except ValueError as error:
        parser.error(str(error))
    return args


def read_test_repository(path):
    """Читает тестовый XML-граф с пакетами из больших латинских букв."""
    root = et.parse(path).getroot()
    if root.tag != "repository":
        raise ValueError("Корень тестового XML должен быть repository")
    graph = {}
    for package in root:
        name, children = read_test_package(package)
        if name in graph:
            raise ValueError(f"Повторное имя пакета: {name}")
        graph[name] = children
    for children in graph.values():
        for child in children:
            if child not in graph:
                raise ValueError(f"В XML отсутствует пакет {child}")
    return graph


def read_test_package(package):
    """Проверяет один пакет тестового XML."""
    name = package.get("name", "")
    if package.tag != "package" or not re.fullmatch(r"[A-Z]+", name):
        raise ValueError("Ожидается package с именем из больших латинских букв")
    children = []
    for dependency in package:
        if dependency.tag != "dependency":
            raise ValueError("В package допустимы только dependency")
        children.append(dependency.get("name", ""))
    return name, children


def pom_value(dependency, name, properties):
    """Читает поле зависимости и подставляет простое локальное свойство."""
    value = (dependency.findtext(name) or "").strip()
    if value.startswith("${") and value.endswith("}"):
        value = properties.get(value[2:-1], "")
    if not value or "${" in value:
        raise ValueError(f"Не удалось определить {name} зависимости")
    return value


def parse_pom(content):
    """Извлекает объявленные прямые зависимости из Maven POM."""
    root = et.fromstring(content)
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]
    if root.tag != "project":
        raise ValueError("Корень Maven POM должен быть project")
    properties = {
        element.tag: (element.text or "").strip()
        for element in root.findall("./properties/*")
    }
    result = []
    for dependency in root.findall("./dependencies/dependency"):
        fields = [
            pom_value(dependency, name, properties)
            for name in ("groupId", "artifactId", "version")
        ]
        coordinate = ":".join(fields)
        if not re.fullmatch(f"{NAME}:{NAME}:{VERSION}", coordinate):
            raise ValueError("Неподдерживаемые координаты зависимости")
        result.append(coordinate)
    return result


def read_dependencies(package, args):
    """Читает POM указанной версии по URL или локальному пути."""
    group, artifact, version = package.split(":")
    relative = (
        f"{group.replace('.', '/')}/{artifact}/{version}/"
        f"{artifact}-{version}.pom"
    )
    if args.mode == "url":
        url = f"{args.repository.rstrip('/')}/{relative}"
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return parse_pom(response.read())
    base = Path(args.repository)
    if base.is_file():
        if package == f"{args.package}:{args.version}":
            return parse_pom(base.read_bytes())
        base = base.parent
    return parse_pom((base / relative).read_bytes())


def build_graph(root, loader, max_depth):
    """Строит граф через стек с учетом более коротких путей."""
    graph = {root: []}
    cache = {}
    depths = {}
    stack = [(root, MIN_DEPTH)]
    while stack:
        package, depth = stack.pop()
        if package in depths and depths[package] <= depth:
            continue
        depths[package] = depth
        graph.setdefault(package, [])
        if depth >= max_depth:
            continue
        if package not in cache:
            cache[package] = list(dict.fromkeys(loader(package)))
        graph[package] = cache[package]
        for child in reversed(graph[package]):
            stack.append((child, depth + STEP))
    return graph


def has_cycle(graph):
    """Обнаруживает цикл нерекурсивным DFS."""
    active = set()
    done = set()
    for root in graph:
        if root in done:
            continue
        stack = [(root, False)]
        while stack:
            package, finished = stack.pop()
            if finished:
                active.remove(package)
                done.add(package)
                continue
            if package in active:
                return True
            if package in done:
                continue
            active.add(package)
            stack.append((package, True))
            for child in reversed(graph[package]):
                stack.append((child, False))
    return False


def load_order(graph, root):
    """Ставит зависимости раньше потребителей, не включая исходный пакет."""
    if has_cycle(graph):
        raise ValueError("Нельзя построить порядок загрузки: обнаружен цикл")
    order = []
    visited = set()
    stack = [(root, False)]
    while stack:
        package, finished = stack.pop()
        if finished:
            if package != root:
                order.append(package)
            continue
        if package in visited:
            continue
        visited.add(package)
        stack.append((package, True))
        for child in reversed(graph[package]):
            stack.append((child, False))
    return order


def print_result(graph, root, args):
    """Печатает граф либо порядок в пределах выбранной глубины."""
    if args.load_order:
        order = load_order(graph, root)
        print(f"Порядок загрузки в пределах глубины {args.max_depth}:")
        if not order:
            print("Нет зависимостей в заданной глубине")
        for index, package in enumerate(order, start=1):
            print(f"{index}. {package}")
        print(f"Исходный пакет: {root}")
    else:
        print("Граф зависимостей в пределах заданной глубины:")
        for package, children in graph.items():
            print(f"{package} -> {', '.join(children) or '[]'}")
        print("Обнаружен цикл" if has_cycle(graph) else "Циклов нет")


def main():
    """Получает данные и выводит построенный граф."""
    args = parse_arguments()
    try:
        if args.mode == "test":
            repository = read_test_repository(args.repository)
            if args.package not in repository:
                raise ValueError("Исходный пакет отсутствует в XML")
            root = args.package
            loader = repository.__getitem__
        else:
            root = f"{args.package}:{args.version}"
            loader = partial(read_dependencies, args=args)
        graph = build_graph(root, loader, args.max_depth)
        print_result(graph, root, args)
        if args.ascii_tree == "y":
            print("ASCII-дерево будет реализовано на этапе 5")
    except (OSError, ValueError, et.ParseError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(ERROR)


if __name__ == "__main__":
    main()