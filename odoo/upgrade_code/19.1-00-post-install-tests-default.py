from __future__ import annotations

import ast
import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def upgrade(file_manager: FileManager):
    tagged_classes_names = set()
    all_classes = []
    for file in file_manager:
        if file.path.suffix != '.py':
            continue
        if file.path.parent.name != 'tests':
            continue

        content = file.content
        ast_tree = ast.parse(content, filename=str(file.path))
        class_defs = [node for node in ast_tree.body if isinstance(node, ast.ClassDef)]
        for class_def in class_defs:
            # skip classes without inheritance
            if not class_def.bases:
                continue

            all_classes.append(class_def)
            for decorator in class_def.decorator_list:
                if isinstance(decorator, ast.Call) and getattr(decorator.func, 'id', None) == 'tagged':
                    arguments = [arg.s for arg in decorator.args if isinstance(arg, ast.Constant) and isinstance(arg.s, str)]
                    if 'post_install' in arguments or 'at_install' in arguments:
                        tagged_classes_names.add(class_def.name)
                    continue

    untagged_classes = all_classes
    stable = False
    while not stable:
        stable = True
        untagged_classes = [cls for cls in untagged_classes if cls.name not in tagged_classes_names]
        for cls in untagged_classes:
            for base in cls.bases:
                if (isinstance(base, ast.Name) and base.id in tagged_classes_names) or (isinstance(base, ast.Attribute) and base.attr in tagged_classes_names):
                    tagged_classes_names.add(cls.name)
                    stable = False
    print(len(untagged_classes))
    print(list(untagged_classes)[0].name)

    untagged_classes_names = sorted(set(cls.name for cls in untagged_classes))

    print(untagged_classes_names)




    return
