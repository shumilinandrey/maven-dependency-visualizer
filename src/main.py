import argparse
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

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


def valid_package(value):
    """Check that a package uses the groupId:artifactId format."""
    if value.count(':') != 1:
        raise argparse.ArgumentTypeError(
            "use Maven format groupId:artifactId"
        )
    return value


def get_pom_relative_path(group_id, artifact_id, version):
    """Формирует относительный путь к pom-файлу по стандарту Maven"""
    group_path = group_id.replace(".", "/")
    filename = f"{artifact_id}-{version}.pom"
    return f"{group_path}/{artifact_id}/{version}/{filename}"


def fetch_pom_content(repository, mode, group_id, artifact_id, version):
    """Считывает pom.xml"""
    if mode == "path" and os.path.isfile(repository):
        with open(repository, "r", encoding="utf-8") as file_handle:
            return file_handle.read()
    rel_path = get_pom_relative_path(group_id, artifact_id, version)
    if mode == "path":
        full_path = os.path.join(repository, rel_path)
        with open(full_path, "r", encoding="utf-8") as file_handle:
            return file_handle.read()
    base_url = repository.rstrip("/")
    target_url = f"{base_url}/{rel_path}"
    req = urllib.request.Request(
        target_url, headers={"User-Agent": "DependencyVisualizer/1.0"}
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8")


def extract_properties(root, namespace):
    """Извлекает словарь значений из блока properties"""
    properties = {}
    props_elem = root.find(f"{namespace}properties")
    if props_elem is not None:
        for prop in props_elem:
            tag = prop.tag.split("}")[-1]
            properties[tag] = (prop.text or "").strip()
    return properties


def apply_property(value, properties):
    """Подставляет значение свойства вида ${name}"""
    if not value.startswith("${") or not value.endswith("}"):
        return value
    key = value[2:-1]
    return properties.get(key, value)


def parse_dependencies(xml_text):
    """Извлекает прямые зависимости из XML-документа"""
    root = ET.fromstring(xml_text)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag[:root.tag.index("}") + 1]
    properties = extract_properties(root, ns)
    deps = []
    deps_elem = root.find(f"{ns}dependencies")
    if deps_elem is None:
        return deps
    for dep in deps_elem.findall(f"{ns}dependency"):
        group_el = dep.find(f"{ns}groupId")
        artifact_el = dep.find(f"{ns}artifactId")
        version_el = dep.find(f"{ns}version")
        scope_el = dep.find(f"{ns}scope")
        group = (
            group_el.text.strip()
            if group_el is not None and group_el.text
            else ""
        )
        artifact = (
            artifact_el.text.strip()
            if artifact_el is not None and artifact_el.text
            else ""
        )
        version = (
            version_el.text.strip()
            if version_el is not None and version_el.text
            else "managed"
        )
        scope = (
            scope_el.text.strip()
            if scope_el is not None and scope_el.text
            else "compile"
        )
        group = apply_property(group, properties)
        artifact = apply_property(artifact, properties)
        version = apply_property(version, properties)
        deps.append((group, artifact, version, scope))
    return deps


def parse_arguments():
    """Считывание аргументов командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--package", required=True, type=valid_package,
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
    group_id, artifact_id = settings.package.split(":", 1)
    try:
        content = fetch_pom_content(
            settings.repository,
            settings.mode,
            group_id,
            artifact_id,
            settings.version
        )
        dependencies = parse_dependencies(content)
        print(f"Прямые зависимости для {settings.package}:{settings.version}:")
        for group, artifact, version, scope in dependencies:
            print(f"  - {group}:{artifact}:{version} [{scope}]")
    except (urllib.error.URLError, OSError, ET.ParseError) as error:
        print(f"Ошибка при получении зависимостей: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()