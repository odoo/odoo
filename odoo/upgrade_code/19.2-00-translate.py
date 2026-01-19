from __future__ import annotations

import ast
import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze code for fields.Html and imports."""

    def __init__(self):
        self.replacements = []  # List of (lineno, col_offset, old_text, new_text)
        self.has_html_translate_import = False

    def visit_ImportFrom(self, node):
        # Check if html_translate is imported
        if node.module and 'translate' in node.module:
            for alias in node.names:
                if alias.name == 'html_translate':
                    self.has_html_translate_import = True
                    break
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check if this is a fields.Html() call
        is_html_field = False
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'Html' and isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'fields':
                    is_html_field = True

        if is_html_field:
            # Check for translate=True and sanitize=False in keywords
            translate_keyword = None
            has_sanitize_false = False
            has_sanitize_email_outgoing = False

            for keyword in node.keywords:
                if keyword.arg == 'translate':
                    if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        translate_keyword = keyword
                elif keyword.arg == 'sanitize':
                    if isinstance(keyword.value, ast.Constant):
                        if keyword.value.value is False:
                            has_sanitize_false = True
                        elif keyword.value.value == 'email_outgoing':
                            has_sanitize_email_outgoing = True

            # If translate=True and no sanitize=False, record this for replacement
            if translate_keyword and not has_sanitize_false and not has_sanitize_email_outgoing:
                self.replacements.append((
                    translate_keyword.value.lineno,
                    translate_keyword.value.col_offset,
                    'True',
                    'html_translate'
                ))

        self.generic_visit(node)


def upgrade(file_manager: FileManager):
    """
    Convert fields.Html(translate=True) to fields.Html(translate=html_translate)
    when sanitize=False is not present, and ensure html_translate is imported.
    """

    # List all Python files that might contain fields.Html
    files = [
        file for file in file_manager
        if file.path.suffix == '.py'
        if file.path.name != '__init__.py'
        if 'fields.Html(' in file.content
    ]

    if not files:
        return

    for fileno, file in enumerate(files, start=1):
        content = file.content

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Skip files that can't be parsed
            file_manager.print_progress(fileno, len(files))
            continue

        # Analyze the code
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)

        if not analyzer.replacements:
            file_manager.print_progress(fileno, len(files))
            continue

        # Replace translate=True with translate=html_translate
        # Sort replacements by line number in reverse order to maintain positions
        analyzer.replacements.sort(reverse=True)

        lines = content.split('\n')
        for lineno, col_offset, old_text, new_text in analyzer.replacements:
            line = lines[lineno - 1]  # lineno is 1-indexed
            # Replace the specific occurrence at col_offset
            before = line[:col_offset]
            after = line[col_offset:]
            if after.startswith(old_text):
                lines[lineno - 1] = before + new_text + after[len(old_text):]

        new_content = '\n'.join(lines)

        # Check if we need to add html_translate import
        if not analyzer.has_html_translate_import:
            new_lines = new_content.split('\n')
            import_pattern = r'^from odoo\.tools\.translate import (.+)$'

            # Check if 'from odoo.tools.translate' exists
            import_found = False
            for i, line in enumerate(new_lines):
                match = re.match(import_pattern, line)
                if match:
                    # Found existing import, add html_translate to it
                    existing_imports = match.group(1).strip()
                    new_lines[i] = f'from odoo.tools.translate import {existing_imports}, html_translate'
                    import_found = True
                    break

            if not import_found:
                # No existing import, add new one in the correct section
                # Import order: 1. import xxx, 2. from non-odoo, 3. from odoo
                last_odoo_import_pos = None
                last_non_odoo_import_pos = None
                new_line = 'from odoo.tools.translate import html_translate'

                for i, line in enumerate(new_lines):
                    if line.startswith('from odoo') and line < new_line:
                        last_odoo_import_pos = i
                    elif line.startswith(('from ', 'import ')):
                        last_non_odoo_import_pos = i
                    elif line.startswith(('def ', 'class ')):
                        break

                insert_pos = (last_odoo_import_pos if last_odoo_import_pos is not None else last_non_odoo_import_pos) + 1
                while insert_pos < len(new_lines) and new_lines[insert_pos] and not new_lines[insert_pos].startswith((' ', '(', ')')):
                    # in case the previous import is
                    # from xxx import (
                    #     aaa,
                    #     bbb,
                    # )
                    last_import_pos = insert_pos
                    while last_import_pos > 0 and new_lines[last_import_pos].startswith(' '):
                        last_import_pos -= 1
                    if last_import_pos < insert_pos:
                        insert_pos = last_import_pos + 1
                    insert_pos += 1

                new_lines.insert(insert_pos, new_line)

            new_content = '\n'.join(new_lines)

        # Write back the file
        file.content = new_content

        file_manager.print_progress(fileno, len(files))
