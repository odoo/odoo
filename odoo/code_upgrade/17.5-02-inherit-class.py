import re
import ast
from pathlib import Path, PurePath

pr = 173996


def upgrade(file_manager):
    model_to_class = import_addon_class_names(file_manager)
    mro = get_addons_mro(file_manager)

    nb = len(list(1 for file in file_manager if file.path.name.endswith('.py')))
    i = 0
    percent = 0
    print(f'   {percent}%')

    for file in file_manager:
        if not file.path.name.endswith('.py'):
            continue

        content = file.content
        addon = file.addon.name
        need_to_import = set()
        for _class_name, _model, class_content in get_class_models(content):
            group_inherit = reg_inherit.search(class_content)
            if not group_inherit:
                continue
            inherit_models =  re.split(r'''[\]\]'", \n]+''', group_inherit.group(2))[1:-1]
            inherit_class = [get_nearest_class(mro, model_to_class, addon, model, file) for model in inherit_models]
            need_to_import.update(depend for depend, _c in inherit_class)
            first_line = class_content.split('\n', 1)[0]
            class_line, rest = first_line.split(')')
            new_class = f'{class_line}, ' + ', '.join(f'{depend}.{class_name}' for depend, class_name in inherit_class) + f'){rest}'
            content = content.replace(first_line, new_class)

        if content != file.content:
            first_line, rest = content.split('\n', 1)
            file.content = f'{first_line}\nfrom odoo.addons import {", ".join(need_to_import)}\n{reg_inherit.sub("", rest)}'

        i += 1
        p = round(i/nb*10) * 10
        if p > percent:
            percent = p
            print(f'   {percent}%')


regex_camel_case = re.compile(r'(?<=.)([A-Z][a-z])|(?<=[a-z])([A-Z]+(?![a-z]))')
def class_name_to_model_name(classname: str) -> str:
    return regex_camel_case.sub(r'.\1\2', classname).lower()


reg_declare_class_name = re.compile(r'^class +(\w+) *\([^)]+Model\b')
def get_class_name(line):
    group_class = reg_declare_class_name.search(line)
    return group_class and group_class.group(1)


reg_name = re.compile(r'''(^|\n)    _name *=[ \n]*(['"][^()'"]+['"])''')
def get_class_models(content):
    classes = []
    iter_lines = iter(content.split('\n'))
    line = next(iter_lines, None)
    while line is not None:
        class_name = get_class_name(line)
        model_lines = [line]
        line = next(iter_lines, None)
        if class_name:
            model = class_name_to_model_name(class_name)
            while line is not None and (not line or line.startswith('  ')):
                group_name = reg_name.search(line)
                if group_name:
                    model = group_name.group(2).strip()[1:-1]
                model_lines.append(line)
                line = next(iter_lines, None)
            classes.append((class_name, model, '\n'.join(model_lines)))
    return classes


reg_inherit = re.compile(r'''(^|\n)    _inherit *=[ \n]*(['"][^()'"]+['"]|(\[([^\]]+)\]))''')
def import_addon_class_names(file_manager) -> dict[str, tuple[str, set, str]]:
    model_to_class: dict[str, tuple[str, set, str]] = {}

    for file in file_manager:
        if not file.path.name.endswith('.py'):
            continue

        content = file.content
        file_classes = set()
        for class_name, model, content in get_class_models(content):
            root = True
            group_inherit = reg_inherit.search(content)
            if group_inherit:
                inherit = re.split(r'''[\]\]'", \n]+''', group_inherit.group(2))[1:-1]
                root = model not in inherit
            file_classes.add((model, class_name, root))

        if not file_classes:
            continue

        # update import parent folder

        parent = file.path.parent
        parent_init = file_manager.get_file(PurePath(parent, Path('__init__.py')))
        if parent_init:
            module = file.path.name[0:-3]
            replacement = rf'\2from .{module} import {", ".join([c for _m, c, _r in file_classes])}\3'
            if replacement in parent_init.content:
                continue
            reg_import = re.compile(rf'from . import (.*?),?(\s*)\b{module}\b(\s*),?(.*?)')
            groups_import = reg_import.search(parent_init.content)
            if groups_import:
                if groups_import.group(1) and groups_import.group(4):
                    replacement = rf'from . import \1,\2 \3\4{replacement}'
                elif groups_import.group(1) or groups_import.group(4):
                    replacement = rf'from . import \1\2\3\4{replacement}'
                parent_init.content = reg_import.sub(replacement, parent_init.content)

        imported = True
        # update import parented folders until addons root
        while imported and parent != file.addon:
            module = parent.name
            parent = parent.parent

            if module in ('demo', 'populate'):
                imported = False
                break

            parent_init = file_manager.get_file(PurePath(parent, Path('__init__.py')))
            if not parent_init:
                imported = False
                break

            if re.search(rf'from [.]{module} import ([*]|.*\b({"|".join(f[1] for f in file_classes)})\b)', parent_init.content):
                continue

            groups_import = re.search(rf'from . import (.*?),?(\s*)\b{module}\b(\s*),?(.*?)', parent_init.content)
            if groups_import:
                replacement = rf'\2from .{module} import *\3'
                if groups_import.group(1) and groups_import.group(4):
                    replacement = rf'from . import \1,\2 \3\4{replacement}'
                elif groups_import.group(1) or groups_import.group(4):
                    replacement = rf'from . import \1\2\3\4{replacement}'
                parent_init.content = reg_import.sub(replacement, parent_init.content)
                continue

            imported = False
            break

        if imported:
            for model, class_name, root in file_classes:
                if model not in model_to_class:
                    model_to_class[model] = (class_name, set(), file.addon.name if root else '?')
                elif root:
                    model_to_class[model] = (model_to_class[model][0], model_to_class[model][1], file.addon.name)
                model_to_class[model][1].add(file.addon.name)

    return model_to_class


def get_addons_mro(file_manager) -> dict[str, list]:
    addon_depends = {}
    for file in file_manager:
        if file.addon.name in addon_depends:
            continue

        manifest = file_manager.get_file(PurePath(file.addon, Path('__manifest__.py')))
        if not manifest:
            continue

        manifest_dict = ast.literal_eval(manifest.content)
        addon_depends[file.addon.name] = manifest_dict.get('depends', []) + ['base']

    addon_depends['base'] = []

    def get_level_depends(addon, level=0):
        local_depends = addon_depends[addon]
        depends = [(level, depend) for depend in local_depends]
        for depend in local_depends:
            depends.extend(get_level_depends(depend, level + 1))
        return depends

    mro: dict[str, list] = {}
    for addon in addon_depends:
        mro[addon] = []
        for _i, depend in sorted(get_level_depends(addon), key=lambda d: -d[0]):
            if depend not in mro[addon]:
                mro[addon].append(depend)
        mro[addon].reverse()
    return mro


def get_nearest_class(mro: dict[str, list], model_to_class: dict[str, tuple[str, set, str]], from_addon: str, model: str, file):
    class_name, addons, root_addon = model_to_class[model]
    if root_addon == from_addon:
        return (root_addon, class_name)
    if from_addon in addons:
        return (root_addon, class_name)
    for depend in mro[from_addon]:
        if depend in addons:
            return (depend, class_name)
    raise ValueError(f'Inherit {model!r} is not possible, the class was not found in the {from_addon!r} dependencies.\n'
                      'Check the manifest and if you have all the necessary addons.\n'
                      f'The model {model!r} is defined in: {addons}\n'
                      f'{from_addon!r} dependencies: {mro[from_addon]}\n'
                      f'Erroneous file: {str(file.path)}')
