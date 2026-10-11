import argparse
import os


def valid_input(value):
    """Проверяет корректность ввода строкового значения"""
    if not value.strip():
        raise argparse.ArgumentTypeError("Значение не может быть пустым")
    return value


def valid_int(value):
    """Проверяет корректность ввода числового значения"""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Значение должно быть числом"
        ) from error
    if number < 0:
        raise argparse.ArgumentTypeError("Значение должно быть неотрицательным")
    return number


def parse_arguments():
    """Считывание аргументов командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--package", required=True, type=valid_input,
        help="Имя анализируемого пакета")
    parser.add_argument(
        "-r", "--repository", required=True, type=valid_input,
        help="URL-адрес репозитория или путь к файлу")
    parser.add_argument(
        "-m", "--mode", required=True, choices=("url", "path"),
        help="Режим работы url/path"
    )
    parser.add_argument(
        "-v", "--version", required=True, type=valid_input,
        help="Версия пакета")
    parser.add_argument(
        "-t", "--ascii-tree", required=True, choices=("y", "n"),
        help="Вывод ascii-дерева y/n"
    )
    parser.add_argument(
        "-d", "--max-depth", required=True, type=valid_int,
        help="Максимальная глубина анализа"
    )
    settings = parser.parse_args()

    if settings.mode == "path":
        if not os.path.isfile(settings.repository):
            parser.error("Указанный файл не существует")
    else:
        link = settings.repository.split("://")
        if link[0] not in ["http", "https"] or len(link) != 2:
            parser.error("Указана неверная ссылка")
    return settings


def main():
    """Точка входа программы"""
    settings = parse_arguments()
    print(f"package={settings.package}")
    print(f"repository={settings.repository}")
    print(f"mode={settings.mode}")
    print(f"version={settings.version}")
    print(f"ascii-tree={settings.ascii_tree}")
    print(f"max-depth={settings.max_depth}")


if __name__ == "__main__":
    main()