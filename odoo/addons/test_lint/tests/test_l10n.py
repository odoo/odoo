# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from .common import LintCase


class L10nChecker(ast.NodeVisitor):
    def add_error(self, node):
        pass

    def matches_tagged(self, node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                return node.func.attr == 'tagged'
            if isinstance(node.func, ast.Name):
                return node.func.id == 'tagged'
        return False

    def visit_ClassDef(self, node):
        tags = {
            arg.value
            for deco in node.decorator_list
            for arg in deco.args
            if self.matches_tagged(deco)
        }
        if (
            (len({'post_install_l10n', 'external_l10n'} & tags) != 1)
            or ('post_install_l10n' in tags and 'post_install' not in tags)
            # or ('post_install_l10n' not in tags and 'post_install' in tags)
            or (('external_l10n' in tags) ^ ('external' in tags))
        ):
            if any(
                stmt.name.startswith('test_')
                for stmt in node.body
                if isinstance(stmt, ast.FunctionDef)
            ):
                self.add_error(node)


class L10nLinter(LintCase):
    def test_l10n_test_tags(self):
        checker = L10nChecker()
        rs = []
        for path in self.iter_module_files('**/l10n_*/tests/*.py'):
            checker.add_error = lambda node: rs.append(f'{path}:{node.lineno}')
            self.visit_python_file(path, checker)

        if rs:
            rs.insert(0, "missing `post_install_l10n` tag at:")
            self.fail("\n- ".join(rs))
