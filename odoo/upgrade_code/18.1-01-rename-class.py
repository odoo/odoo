import re


def upgrade(file_manager):
    files = [file for file in file_manager if file.path.name.endswith('.py')]
    file_manager.print_progress(0, len(files))

    for count, file in enumerate(files, start=1):
        model_classes = get_model_classes(file)
        content = file.content
        content = rename_model_classes(content, model_classes)
        content = update_model_name_inherit(content)
        content = update_blank_lines(content)
        file.content = content
        file_manager.print_progress(count, len(files))


# matches the places where to insert a '.' in class_name_to_model_name()
RE_DOT_PLACE = re.compile(r"(?<=[^_])([A-Z])")

# matches all the lines like one of those:
#   class <identifier> (... Model ...
#       _name = <str>
#       _inherit = <str>
RE_MODEL_DEF = re.compile(
    r"""
        (
            ^class \s+ (?P<class>\w+) \s* \( .*
            \b (Model|TransientModel|AbstractModel|BaseModel) \b
        )|(
            ^\s{4,8} (?P<attr>_name|_inherit) \s* = \s*
            (?P<attrs> (\w+ \s* = \s*)*)
            (?P<quote>['"]) (?P<model>[\w.]+) (?P=quote)
        )
    """,
    re.VERBOSE)

# matches model classes with preceding blank lines and comments
RE_CLASS_DEF = re.compile(
    r"""
        (^ \n)*
        (?P<comments> (^ [#] .* \n)* )
        (?P<class> ^ class .* \b (Model|TransientModel|AbstractModel|BaseModel) \b )
    """,
    re.MULTILINE | re.VERBOSE,
)


def class_name_to_model_name(class_name: str) -> str:
    return RE_DOT_PLACE.sub(r'.\1', class_name).lower()


def model_name_to_class_name(model_name: str) -> str:
    return "".join(
        part[0].upper() + part[1:]
        for part in model_name.replace('_', '_.').split('.')
        if part
    )


def get_model_classes(file):
    """ Return a dict mapping class names to their corresponding model name. """
    result = {}

    def collect(class_name, model_info):
        if model_info:
            model_name = model_info.get('_name') or model_info.get('_inherit')
            other_name = result.setdefault(class_name, model_name)
            if other_name != model_name:
                raise ValueError(
                    f"Class name {class_name!r} in addon {file.addon.name!r} "
                    f"is used for both models {other_name!r} and {model_name!r}. "
                    "Please rename one of the classes before running the script."
                )

    class_name = None
    model_info = {}

    for line in file.content.splitlines():
        match = RE_MODEL_DEF.match(line)
        if not match:
            continue

        if match['class']:
            # we found a class definition
            collect(class_name, model_info)
            class_name = match['class']
            model_info.clear()

        elif class_name and match['model']:
            # we found a model name (_name or _inherit with string)
            model_info[match['attr']] = match['model']

    collect(class_name, model_info)

    return result


def rename_model_classes(content, model_classes):
    spattern = r"^[^']*('[^']*'[^']*)*'[^']*$"      # odd number of single quotes
    dpattern = r'^[^"]*("[^"]*"[^"]*)*"[^"]*$'      # odd number of double quotes
    re_bad = re.compile(rf"#| fields\.|self\.$|{spattern}|{dpattern}")
    re_sql = re.compile(r"\b(SELECT|FROM|JOIN|ON|WHERE|AND|OR|GROUP|UNION)\b")
    lines = content.split("\n")

    for old_class_name, model_name in model_classes.items():
        new_class_name = model_name_to_class_name(model_name)
        if old_class_name == new_class_name:
            continue

        re_class = re.compile(rf"\b{old_class_name}\b")
        re_super = re.compile(rf"super\(\s*{new_class_name}\s*,\s*self\s*\)")
        for index, line in enumerate(lines):
            before = line.split(old_class_name, 1)[0]
            if not (re_bad.search(before) or re_sql.search(line)):
                line = re_class.sub(new_class_name, line)
                line = re_super.sub('super()', line)
                lines[index] = line

    return "\n".join(lines)


def update_model_name_inherit(content):
    result = []

    class_name = None
    for line in content.split("\n"):
        # by default, keep the line as is
        result.append(line)

        match = RE_MODEL_DEF.match(line)
        if not match:
            continue

        if match['class']:
            # we found a class definition
            class_name = match['class']

        elif class_name and match['model']:
            # we found a model name (_name or _inherit with string)
            model_name = match['model']
            same_as_class = class_name_to_model_name(class_name) == model_name

            if match['attr'] == '_name' and same_as_class:
                # _name can be inferred from class name, so drop _name
                if match['attrs']:
                    result[-1] = re.sub(r"\b_name\s*=\s*", "", line)
                else:
                    result.pop()

            elif match['attr'] == '_inherit' and not same_as_class:
                # _name and _inherit are not the same, wrap _inherit in a list
                index0 = match.start('quote')
                index1 = match.end('model') + 1
                result[-1] = f"{line[:index0]}[{line[index0:index1]}]{line[index1:]}"

    return "\n".join(result)


def update_blank_lines(content):
    """ Replace multiple blank lines before class definitions into exactly 2 blank lines. """
    return RE_CLASS_DEF.sub(r"\n\n\g<comments>\g<class>", content)
