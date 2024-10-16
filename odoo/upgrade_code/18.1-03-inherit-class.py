import re
import ast
from pathlib import Path, PurePath
from collections import defaultdict

"""
This script convert "_inherit" model attribute into a python inheritance.
"""

regex_class_name = re.compile(r'''((?<=\n)class ([\w]+)\s*\(.*(?:TransientModel|AbstractModel|Model)[,)].*(?:\n| +.*)*)''')
regex_class_replace = re.compile(r'''^(class [^(]+)\(([^)]+)\)''')
reg_inherit = re.compile(r'''(?:^|\n)    _inherit *=[ \n]*\[([^\]]+)\]''')
reg_imported_class = re.compile(r'''(?:from \..*?|    |\(|, *)\b([A-Z]\w+)\b''')
BLACKLIST_ADDON_FOR_IMPORT = set() # {'base_setup', 'web_tour', 'bus', 'html_editor'}


def upgrade(file_manager):
    mro = get_addons_mro(file_manager)
    addon_classes = get_available_addon_classes(file_manager)

    nb = len(list(1 for file in file_manager if file.path.name.endswith('.py')))
    i = 0
    file_manager.print_progress(i, nb)

    for file in file_manager:
        if not file.path.name.endswith('.py'):
            continue

        content = file.content
        addon = file.addon.name
        need_to_import = set()
        for class_name, inherit_classes, class_content in get_class_with_inherit(content):
            is_root = addon in (get_nearest_class_addons(mro, addon_classes, addon, class_name, file) or [])
            imported_classes = []
            for class_name in inherit_classes:
                depends = get_nearest_class_addons(mro, addon_classes, addon, class_name, file)
                if not depends:
                    break
                need_to_import.update(depends)
                for depend in depends:
                    imported_class = f'{depend}.{class_name}'
                    if imported_class not in imported_classes:
                        imported_classes.append(imported_class)
            else:
                new_class_content = reg_inherit.sub('', class_content)
                replacement = rf"\1(\2, {', '.join(imported_classes)})" if is_root else rf"\1({', '.join(imported_classes)})"
                new_class_content = regex_class_replace.sub(replacement, new_class_content)
                content = content.replace(class_content, new_class_content)

        if content != file.content:
            lines = content.split('\n')
            index = 1
            for n, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    index = n
            lines.insert(index + 1, f'from odoo.addons import {", ".join(need_to_import)}')
            content = '\n'.join(lines)
            file.content = content

        i += 1
        file_manager.print_progress(i, nb)


def model_name_to_class_name(model):
    return ''.join([
        part[0].upper() + part[1:]
        for part in re.split(r'\.', model.replace('_', '_.'))
        if part
    ])


TYPE_ADDON_CLASSES = dict[str, set[str]]


def get_available_addon_classes(file_manager) -> TYPE_ADDON_CLASSES:
    classes = defaultdict(set)
    for file in file_manager:
        if file.addon == file.path.parent and file.path.name == '__init__.py':
            for c in reg_imported_class.findall(file.content):
                classes[c].add(file.addon.name)
    return classes


TYPE_CLASS_INHERIT = list[tuple[str, list[str], str]]


def get_class_with_inherit(content: str) -> TYPE_CLASS_INHERIT:
    """ return the list of the models with "_inherit" content and the class name needed.
    """
    classes_with_inherit = []
    for class_content, class_name in regex_class_name.findall(content):
        g_inherit = reg_inherit.search(class_content)
        if not g_inherit:
            continue
        inherit_models = [m.strip().strip('"').strip("'") for m in g_inherit.group(1).split(',')]
        inherit_classes = [model_name_to_class_name(m) for m in inherit_models if m]
        classes_with_inherit.append((class_name, inherit_classes, class_content.strip()))
    return classes_with_inherit


TYPE_MRO = dict[str, list[list[str]]]


def get_addons_mro(file_manager) -> TYPE_MRO:
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
        depends = [(level, depend) for depend in local_depends if depend != 'base']
        for depend in local_depends:
            depends.extend(get_level_depends(depend, level - 1))
        return depends

    mro: TYPE_MRO = {}
    for addon in addon_depends:
        depends = set()
        sorted_depends = sorted(get_level_depends(addon), key=lambda d: -d[0])
        pre_mro: list[list[str]] = [[] for _x in range(100)]
        for level, depend in sorted_depends:
            if depend not in depends:
                depends.add(depend)
                pre_mro[-level].append(depend)
        mro[addon] = [pre for pre in pre_mro if pre] + [['base']]
    return mro


def get_nearest_class_addons(mro: TYPE_MRO, addon_classes: TYPE_ADDON_CLASSES, from_addon: str, class_name: str, file):
    addons = addon_classes[class_name]
    for depends in mro[from_addon]:
        defined = set(depends) & addons - BLACKLIST_ADDON_FOR_IMPORT
        if defined:
            return [depend for depend in depends if depend in addons]
    if from_addon in addons:
        return [from_addon]
    return None
