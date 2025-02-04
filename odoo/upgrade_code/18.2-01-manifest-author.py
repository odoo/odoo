import ast
import re
import sys
from os import fspath

AUTHOR = "Odoo S.A."  # @contributors, change me :)

def upgrade(file_manager):
    license_re = re.compile(r'''^(?P<indent>[ \t]*)(?P<quote>["'])license''', re.M)

    files = [f for f in file_manager if f.path.name == '__manifest__.py']
    for fileno, file in enumerate(files, start=1):
        manifest = ast.literal_eval(file.content)
        if 'author' not in manifest:
            match = license_re.search(file.content)
            if match:
                pos = match.span()[0]
                author = '{i}{q}author{q}: {q}{author}{q},\n'.format(
                    author=AUTHOR, i=match['indent'], q=match['quote']
                )
                file.content = file.content[:pos] + author + file.content[pos:]
            else:
                print("missing author and license in", fspath(file.path), file=sys.stderr)

        file_manager.print_progress(fileno, len(files))
