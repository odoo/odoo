"""
Tuple-ify _rec_names_search.

    - _rec_names_search = ['name']
    + _rec_names_search = ('name',)
"""
import re


def upgrade(file_manager):
    files = [
        file for file in file_manager
        if 'models' in file.path.parts
        if file.path.suffix == '.py'
        if file.path.name != '__init__.py'
    ]

    if not files:
        return

    rec_names_search_re = re.compile(r'''
        ^\ {4}_rec_names_search\s*=\s*\[        # _rec_names_search = [
            (?:\s*(?:'[\w.]+'|"[\w.]+")\s*,?)*  #     'field1', "field2",
        \]\s*(?:[#].*)?$                        # ]  # maybe a comment
    ''', re.MULTILINE | re.VERBOSE)

    def replace(match):
        return (match[0]
            .replace('[', '(')
            .replace(']', ')' if ',' in match[0] else ',)')
        )

    for fileno, file in enumerate(files, start=1):
        file.content = rec_names_search_re.sub(replace, file.content)
        file_manager.print_progress(fileno, len(files))
