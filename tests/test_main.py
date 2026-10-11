import argparse
import sys

import pytest
from src.main import main, parse_arguments, valid_input, valid_int


def valid_args():
    """Набор правильных аргументов"""
    return [
        "--package", "name",
        "--repository", "https://github.com",
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

    assert settings.package == "name"
    assert settings.mode == "url"
    assert settings.max_depth == 2


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