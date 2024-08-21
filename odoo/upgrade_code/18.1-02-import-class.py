import re
from pathlib import Path, PurePath
from collections import defaultdict

"""
This script exposes Odoo class models at root level to make them available to other addons.
"""

regex_class_name = re.compile(r'(?:\n|^)class ([\w]+)\s*\(.*(?:TransientModel|AbstractModel|Model)[,)]')
regex_name = re.compile(r'class (.*)\(.*(?:\n[^(]*?)    _name *=.*')
regex_inherit = re.compile(r'''class (.*)\(.*(?:\n[^(]*?)    _inherit *= *['"]''')


def upgrade(file_manager):
    nb = sum(1 for file in file_manager if file.path.name.endswith(".py"))
    i = 0
    file_manager.print_progress(i, nb)

    class_to_import = defaultdict(dict)

    for file in file_manager:
        if not file.path.name.endswith(".py"):
            continue

        i += 1
        file_manager.print_progress(i, nb)

        # Import all odoo classes which have model name matching class name
        file_classes = set(regex_class_name.findall(file.content)) - set(regex_name.findall(file.content)) - set(regex_inherit.findall(file.content))
        if not file_classes:
            continue

        # Updated imports so that classes are imported in their parent (Most of the time it is about "models" folder)
        modules = []
        parent = file.path
        addon_init = None
        while parent != file.addon:
            addon_init = file_manager.get_file(PurePath(parent.parent, Path("__init__.py")))
            if not addon_init:
                break

            modules.append(parent.stem)

            if not (re.search(rf"from *\.\b{parent.stem}\b", addon_init.content) or
                    re.search(rf"from *\.\b{'.'.join(reversed(modules))}\b", addon_init.content) or
                    re.search(rf"from *\. +import .*\b{parent.stem}\b", addon_init.content)):
                addon_init = None
                break

            parent = parent.parent

        if not addon_init:
            continue

        module_paths = tuple(reversed(modules))
        class_to_import[addon_init][module_paths] = file_classes

    for addon_init, imported_modules in class_to_import.items():
        # Sorts by defined imports to import only the last occurrence
        module_paths = sorted(imported_modules.keys(), key=lambda module_path: get_module_order_key(file_manager, addon_init, module_path))
        content = addon_init.content

        imported_classes = set()
        imports = []
        for module_path in module_paths:
            file_classes = imported_modules[module_path] - imported_classes
            class_names = {c for c in file_classes if not re.search(rf"\b{c}\b", content)}
            imported_classes.update(file_classes)
            if class_names:
                # Some classes must be imported
                imports.append(join_classes_to_string_import(module_path, class_names))
        if not imports:
            continue

        import_ref = re.findall(r"(?:^|\n)(from.* import [^\n]*)", content)[-1]
        index = content.index(import_ref) + len(import_ref)
        imports_str = "\n".join(sorted(imports))
        content = f"{content[:index]}\n\n{imports_str}\n{content[index + 1:]}"
        if content[-1] != "\n":
            content += "\n"
        addon_init.content = content


def get_module_order_key(file_manager, addon_init, module_paths: tuple[str]) -> tuple[int]:
    path = addon_init.path.parent
    content = addon_init.content
    indexes = []
    for module in module_paths[:-1]:
        indexes.append(-content.index(module))
        path = PurePath(path, Path(module))
        content = file_manager.get_file(PurePath(path, Path('__init__.py'))).content
    indexes.append(-content.index(module_paths[-1]))
    return tuple(indexes)


def join_classes_to_string_import(module_path, class_names):
    """ return to string representing the import to be done for the classes.
        Automatically wraps lines to write lines of up to 100 characters.
    """
    import_str = rf"from .{'.'.join(module_path)} import"
    line_len = len(import_str)
    classes_str = ""
    multiline = sum(len(c) + 2 for c in class_names) + len(import_str) > 95  # github editor size
    for c in sorted(class_names):
        line_len += len(c) + 2  # space and commat
        part = f" {c},"
        if line_len > 95:
            part = f"\n    {c},"
            line_len = len(part)
        classes_str += part
    classes_str = classes_str[1:]
    return f"{import_str} (\n    {classes_str}\n)" if multiline else f"{import_str} {classes_str[:-1]}"
