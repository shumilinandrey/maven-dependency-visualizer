import argparse
import sys

import pytest
from src.main import valid_input, valid_int, valid_package
from src.main import parse_arguments


EXPECTED_DEPTH = 2


def valid_args():
    """Набор правильных аргументов"""
    return [
        "--package", "org.apache.commons:commons-lang3",
        "--repository", "https://repo.maven.apache.org/maven2",
        "--mode", "url",
        "--version", "1.0",
        "--ascii-tree", "n",
        "--max-depth", "2",
    ]


def test_valid_input():
    """Проверка корректного строкового параметра"""
    assert valid_input("name") == "name"


def test_empty_input():
    """Проверка пустого строкового параметра"""
    with pytest.raises(argparse.ArgumentTypeError):
        valid_input("")


def test_valid_package():
    """Проверка корректного Maven-координата"""
    package = "org.apache.commons:commons-lang3"
    assert valid_package(package) == package


def test_invalid_package():
    """Проверка некорректного Maven-координата"""
    with pytest.raises(argparse.ArgumentTypeError):
        valid_package("abcd")


def test_valid_int():
    """Проверка корректного числового параметра"""
    assert valid_int("123") == 123


def test_invalid_int():
    """Проверка некорректного числового параметра"""
    with pytest.raises(argparse.ArgumentTypeError):
        valid_int("-1")


def test_parse_arguments(monkeypatch):
    """Проверка парсинга аргументов"""
    monkeypatch.setattr(sys, "argv", ["main.py", *valid_args()])

    settings = parse_arguments()

    assert settings.package == "org.apache.commons:commons-lang3"
    assert settings.mode == "url"
    assert settings.max_depth == EXPECTED_DEPTH


def test_missing_arguments(monkeypatch):
    """Проверка обработки несуществующих аргументов"""
    monkeypatch.setattr(sys, "argv", ["main.py"])

    with pytest.raises(SystemExit):
        parse_arguments()


def test_invalid_mode(monkeypatch):
    """Проверка указания некорректного режима работы"""
    arguments = valid_args()
    arguments[arguments.index("--mode") + 1] = "other"
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])

    with pytest.raises(SystemExit):
        parse_arguments()


def test_invalid_ascii_tree(monkeypatch):
    """Проверка указания некорректного параметра для ascii-дерева"""
    arguments = valid_args()
    arguments[arguments.index("--ascii-tree") + 1] = "yes"
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])
    with pytest.raises(SystemExit):
        parse_arguments()


def test_invalid_repository(monkeypatch):
    """Проверка указания некорректной ссылки"""
    arguments = valid_args()
    arguments[arguments.index("--repository") + 1] = "ftp://example.org"
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])
    with pytest.raises(SystemExit):
        parse_arguments()


def test_missing_test_file(monkeypatch):
    """Проверка указания несуществующего файла"""
    arguments = valid_args()
    arguments[arguments.index("--mode") + 1] = "path"
    arguments[arguments.index("--repository") + 1] = "missing.txt"
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])
    with pytest.raises(SystemExit):
        parse_arguments()


def test_invalid_package_argument(monkeypatch):
    """Проверка указание некорректного пакеджа"""
    arguments = valid_args()
    arguments[arguments.index("--package") + 1] = "commons-lang3"
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])

    with pytest.raises(SystemExit):
        parse_arguments()