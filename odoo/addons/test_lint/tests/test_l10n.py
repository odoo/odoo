# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import itertools
import os

from . import lint_case


class L10nChecker(lint_case.NodeVisitor):
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
            or ('external_l10n' in tags and 'external' not in tags)
            or ('external_l10n' not in tags and 'external' in tags)
        ):
            return [node]
        return []


class L10nLinter(lint_case.LintCase):
    def test_l10n_test_tags(self):
        checker = L10nChecker()
        rs = []
        for path in self.iter_module_files('**/l10n_*/tests/*.py'):
            with open(path, 'rb') as f:
                t = ast.parse(f.read(), path)
            rs.extend(zip(itertools.repeat(os.path.relpath(path)), checker.visit(t)))

        rs.sort(key=lambda t: t[0])
        assert not rs, "missing `post_install_l10n` tag at\n" + '\n'.join(
            "- %s:%d" % (path, node.lineno)
            for path, node in rs
        )
