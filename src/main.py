import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError

from src.graph import build_graph, find_cycles
from src.repository import MavenRepository, read_test_repository

SUCCESS = 0
ERROR = 1
MIN_DEPTH = 0
MAVEN_NAME = r"[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+"
VERSION = r"[A-Za-z0-9_+.-]+"


def valid_input(value):
    """Отклоняет пустое строковое значение."""
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("Значение не может быть пустым")
    return value


def valid_int(value):
    """Принимает только неотрицательную целую глубину."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Ожидается целое число") from error
    if number < MIN_DEPTH:
        raise argparse.ArgumentTypeError("Глубина не может быть отрицательной")
    return number


def create_parser():
    """Объявляет параметры командной строки."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--package", required=True, type=valid_input)
    parser.add_argument("-r", "--repository", required=True, type=valid_input)
    parser.add_argument(
        "-m", "--mode", required=True, choices=("url", "path", "test")
    )
    parser.add_argument("-v", "--version", required=True, type=valid_input)
    parser.add_argument(
        "-t", "--ascii-tree", required=True, choices=("y", "n")
    )
    parser.add_argument("-d", "--max-depth", required=True, type=valid_int)
    return parser


def validate_url(repository, parser):
    """Проверяет схему, сервер и отсутствие параметров в URL."""
    address = urlsplit(repository)
    if address.scheme not in ("http", "https") or not address.hostname:
        parser.error("Требуется URL репозитория с http или https")
    if address.query or address.fragment:
        parser.error("URL репозитория не должен содержать query/fragment")


def validate_settings(settings, parser):
    """Проверяет параметры с учетом выбранного режима."""
    pattern = r"[A-Z]+" if settings.mode == "test" else MAVEN_NAME
    if re.fullmatch(pattern, settings.package) is None:
        parser.error("Имя пакета: A, B, C для test; groupId:artifactId иначе")
    if re.fullmatch(VERSION, settings.version) is None:
        parser.error("Некорректная версия пакета")
    if settings.version in (".", ".."):
        parser.error("Некорректная версия пакета")
    if settings.mode == "url":
        validate_url(settings.repository, parser)
    else:
        path = Path(settings.repository)
        if not path.exists():
            parser.error("Путь к репозиторию не существует")
        if settings.mode == "test" and not path.is_file():
            parser.error("Для test требуется XML-файл")


def parse_arguments(argv=None):
    """Читает и проверяет аргументы CLI."""
    parser = create_parser()
    settings = parser.parse_args(argv)
    try:
        validate_settings(settings, parser)
    except ValueError as error:
        parser.error(str(error))
    return settings


def get_source(settings):
    """Возвращает корневой узел и функцию получения зависимостей."""
    if settings.mode == "test":
        repository = read_test_repository(settings.repository)
        if settings.package not in repository:
            raise ValueError("Корневого пакета нет в тестовом репозитории")
        return settings.package, repository.__getitem__
    root = f"{settings.package}:{settings.version}"
    repository = MavenRepository(settings.repository, settings.mode, root)
    return root, repository.get_dependencies


def print_graph(graph, cycles):
    """Печатает список смежности и найденные циклы."""
    print("Граф зависимостей в пределах заданной глубины:")
    for package, dependencies in graph.items():
        print(f"{package} -> {', '.join(dependencies) or '[]'}")
    if not cycles:
        print("В построенном графе циклы не обнаружены")
    for cycle in cycles:
        print("Цикл: " + " -> ".join(cycle))


def main(argv=None):
    """Выполняет анализ; ошибки данных направляет в stderr."""
    settings = parse_arguments(argv)
    try:
        root, loader = get_source(settings)
        graph = build_graph(root, loader, settings.max_depth)
        print_graph(graph, find_cycles(graph))
        if settings.ascii_tree == "y":
            print("Вывод ASCII-дерева будет реализован на этапе 5")
        return SUCCESS
    except (OSError, ValueError, ParseError) as error:
        print(f"Ошибка анализа: {error}", file=sys.stderr)
        return ERROR


if __name__ == "__main__":
    sys.exit(main())