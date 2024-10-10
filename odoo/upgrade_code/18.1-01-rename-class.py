import re


def upgrade(file_manager):
    nb = len([1 for file in file_manager if file.path.name.endswith('.py')])
    i = 0
    file_manager.print_progress(0, nb)

    for file in file_manager:
        if not file.path.name.endswith('.py'):
            continue

        class_name_models = get_class_name_models(file)
        content = file.content
        content = update_class_name(content, class_name_models)
        content = remove_name_and_update_inherit(content)
        content = class_with_2_blank_lines(content)
        file.content = content

        i += 1
        file_manager.print_progress(i, nb)


regex_camel_case = re.compile(r'(?<=[^_])([A-Z])')
regex_class_name = re.compile(r'^class ([\w]+)\s*\(.*(TransientModel|AbstractModel|Model)[,)]')


def class_name_to_model_name(classname: str) -> str:
    return regex_camel_case.sub(r'.\1', classname).lower()


def model_name_to_class_name(model):
    return ''.join([
        part[0].upper() + part[1:]
        for part in re.split(r'\.', model.replace('_', '_.'))
        if part
    ])


def attribute_to_model_name(line):
    if '(' in line or ',' in line:
        return
    if '[' in line:
        # makes the code idempotent
        return
    if '"' not in line and "'" not in line:
        return
    if line.startswith('     ') or line.strip().startswith('#'):
        return
    if not line.split('=', 1)[0].strip() in ('_name', '_inherit'):
        return
    return re.sub(r'''[\]\['"\s\n]+''', '', line.split('=').pop())


def get_class_name_models(file):
    content = file.content
    class_name_models = {}
    iter_lines = iter(content.split('\n'))
    line = next(iter_lines, None)
    while line is not None:
        part = regex_class_name.search(line)
        line = next(iter_lines, None)

        if not part:
            continue

        class_name = part.group(1)
        current_model_name = None
        while line is not None and (not line or line.startswith('  ')):
            class_model_name = attribute_to_model_name(line)
            if class_model_name and ('_name' in line or ('_inherit' in line and not current_model_name)):
                current_model_name = class_model_name
            line = next(iter_lines, None)

        if current_model_name and current_model_name != 'base':
            new_class_name = model_name_to_class_name(current_model_name)

            previous = class_name_models.get(class_name)
            if previous and previous[1] != current_model_name:
                raise ValueError(f'Please fix your class {class_name!r} from addon {file.addon.name!r} used for {previous[1]!r} and {current_model_name!r} ({file.path})')

            class_name_models[class_name] = (new_class_name, current_model_name)
    return class_name_models


def update_class_name(content, class_name_models):
    # update class name
    lines = content.split('\n')
    for old_class_name, (new_class_name, _current_model_name) in class_name_models.items():
        if old_class_name == new_class_name:
            continue
        if old_class_name == new_class_name:
            # to avoid unwanted changes (classes having the table name)
            continue

        reg_use_class_name = re.compile(rf'\b{old_class_name}\b')
        reg_use_super = re.compile(rf'super\(\s*{new_class_name}\s*,\s*self\s*\)')
        for index, line in enumerate(lines):
            try:
                start = line.split(old_class_name, 1)[0]
                if "#" in start or ' fields.' in start or start.endswith('self.') or start.count('"') % 2 or start.count("'") % 2:
                    continue
                if (" FROM " in line or
                    "JOIN " in line or
                    " UNION " in line or
                    " AND " in line or
                    " ON " in line or
                    " OR " in line or
                    " WHERE " in line or
                    " GROUP BY " in line or
                    " SELECT " in line):
                    continue
                line = reg_use_class_name.sub(new_class_name, line)
                line = reg_use_super.sub('super()', line)
                lines[index] = line
            except ValueError:
                continue
    return '\n'.join(lines)


def remove_name_and_update_inherit(content):
    lines = content.split('\n')
    length = len(lines)

    class_model_name = None
    for index, line in enumerate(lines):
        if index >= length:
            continue

        part = regex_class_name.search(line)
        if not part:
            continue
        class_name = part.group(1)
        if not class_name:
            continue
        class_model_name = class_name_to_model_name(class_name)

        model_name = None
        index_name = -1
        inherit_model_name = None
        index_inherit = -1
        for i in range(index + 1, length):
            new_line = lines[i]
            if new_line.startswith('class ') or line.startswith('def '):
                break
            new_model_name = attribute_to_model_name(new_line)
            if new_model_name:
                if '_name' in new_line:
                    model_name = new_model_name
                    index_name = i
                elif '_inherit' in new_line and '_inherits' not in new_line:
                    inherit_model_name = new_model_name
                    index_inherit = i

        # update `_inherit` = 'xxx' into `_inherit` = ['xxx']
        if index_inherit != -1:
            inherit_line = lines[index_inherit]
            if '[' not in inherit_line:
                # makes the code idempotent
                attr, value = inherit_line.split('=')
                lines[index_inherit] = f'{attr.rstrip()} = [{value.strip()}]'

        if model_name:
            if class_model_name == model_name:
                if len(lines[index_name].split('=')) > 2:
                    lines[index_name] = re.sub(r'_name *= *', '', lines[index_name])
                else:
                    lines.pop(index_name)
                length -= 1
        elif inherit_model_name and class_model_name != inherit_model_name:
            inherit_line = lines[index_inherit]
            tab = inherit_line[0:(len(inherit_line) - len(inherit_line.lstrip()))]
            lines.insert(index_inherit, f'{tab}_name = "{inherit_model_name}"\n')
            length += 1

    return '\n'.join(lines)


def class_with_2_blank_lines(content):
    """ Replace multiple blank lines before class definitions into exactly 2 blank lines. """
    return re.sub(r'(?:\s*\n)+?(# .*\n)?(class .*Model\))', r'\n\n\n\1\2', content)
