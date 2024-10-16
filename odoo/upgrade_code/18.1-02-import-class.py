import re
from pathlib import Path, PurePath

"""
This script exposes Odoo class models at root level to make them available to other addons.
"""

regex_class_name = re.compile(r'(?:\n|^)class ([\w]+)\s*\(.*(?:TransientModel|AbstractModel|Model)[,)]')
regex_name = re.compile(r'class (.*)\(.*(?:\n[^(]*?)    _name *=.*')
regex_inherit = re.compile(r'''class (.*)\(.*(?:\n[^(]*?)    _inherit *= *['"]''')


def upgrade(file_manager):
    return
    nb = sum(1 for file in file_manager if file.path.name.endswith('.py'))
    i = 0
    file_manager.print_progress(i, nb)

    for file in file_manager:
        if not file.path.name.endswith('.py'):
            continue

        # Import all odoo classes which have model name matching class name
        file_classes = set(regex_class_name.findall(file.content)) - set(regex_name.findall(file.content)) - set(regex_inherit.findall(file.content))
        if not file_classes:
            continue

        # Updated imports so that classes are imported in their parent (Most of the time it is about 'models' folder)
        parent = file.path
        while parent != file.addon:
            module = parent.name.split('.')[0]
            parent = parent.parent

            parent_init = file_manager.get_file(PurePath(parent, Path('__init__.py')))
            if not parent_init:
                break

            content = parent_init.content

            class_names = {c for c in file_classes if not re.search(rf'\b{c}\b', content)}
            if not class_names:
                continue

            # from .xxx import (a, b, c)
            # will be:
            # from .xxx import (a, b, c, d, e, f)
            reg_import_item = re.compile(rf'(from *\.\b{module}\b +import )(\([^)]*\)|[^\n#]*)')
            import_item = reg_import_item.search(content)
            if import_item:
                if '*' not in import_item.group(2):
                    class_names = {c.strip() for c in import_item.group(2).strip('(').strip(')').split(',') if c.strip()} | class_names
                content = reg_import_item.sub(join_classes_to_string_import(module, class_names), content)
                parent_init.content = content
                if content[-1] != "\n":
                    content += "\n"
                continue

            # from . import xxx, yyy
            # will be:
            # from . import yyy
            # from .xxx import (d, e, f)
            reg_import = re.compile(rf'from *\. +import +([^#\n]*?),?( *)\b{module}\b( *),?(.*?)\n')
            groups_import = reg_import.search(content)
            if not groups_import:
                break

            before = groups_import.group(1)
            after = groups_import.group(4)
            if before and after:
                replacement = rf'from . import \1, \4\n{join_classes_to_string_import(module, class_names)}\n'
            elif before:
                replacement = rf'from . import \1\n{join_classes_to_string_import(module, class_names)}\n'
            elif after:
                if after.strip().startswith('#'):
                    if 'noqa' in after.strip():
                        replacement = rf"{join_classes_to_string_import(module, class_names)}\n"
                    else:
                        replacement = rf"{join_classes_to_string_import(module, class_names)}  {after.strip()}\n"
                else:
                    replacement = rf'from . import \3\4\n{join_classes_to_string_import(module, class_names)}\n'
            elif groups_import.group(3).strip():
                replacement = rf"{join_classes_to_string_import(module, class_names)}  {groups_import.group(3).strip()}\n"
            else:
                replacement = rf"{join_classes_to_string_import(module, class_names)}\n"
            content = reg_import.sub(replacement, content)
            if content[-1] != "\n":
                content += "\n"
            parent_init.content = content
            continue

        i += 1
        file_manager.print_progress(i, nb)


def join_classes_to_string_import(module_name, class_names):
    """ return to string representing the import to be done for the classes.
        Automatically wraps lines to write lines of up to 100 characters.
    """
    import_str = rf'from .{module_name} import'
    line_len = len(import_str)
    classes_str = ""
    multi_line = False
    for c in sorted(class_names):
        line_len += len(c) + 2  # space and commat
        part = f" {c},"
        if line_len > 99:
            part = f"\n    {c},"
            line_len = len(part)
            multi_line = True
        classes_str += part
    classes_str = classes_str[1:]
    return f"{import_str} (\n    {classes_str}\n)" if multi_line else f"{import_str} {classes_str[:-1]}"
