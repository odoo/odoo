import ast
import os
import pathlib
import unittest.mock
from collections import Counter

from odoo.addons.test_lint.tests.lint_case import LintCase
from odoo.modules import Manifest


class InitChecker(ast.NodeVisitor):
    def __init__(self):
        self.path = None
        self.names = Counter()
        self.prefix = ''
    def visit_Import(self, node):
        raise AssertionError(f"Init files should not have top-level imports, found {ast.dump(node)}")
    def visit_ImportFrom(self, node):
        assert node.level == 1, f"{ast.dump(node)} should be a `from . import ...`"

        if node.module:
            assert '.' not in node.module, "only supports one level of relative import"
            [alias] = node.names
            assert (alias.name, alias.asname) == ('*', None), \
                f"only star-imports can be used to import test sub-modules, got {ast.dump(node)}"
            with unittest.mock.patch.object(self, 'prefix', f'{self.prefix}{node.module}/'):
                init = self.path / self.prefix / '__init__.py'
                self.visit(ast.parse(init.read_bytes(), init))
        else:
            for alias in node.names:
                if alias.name.startswith('test_'):
                    self.names[f'{self.prefix}{alias.name}.py'] += 1


class TestTestHoles(LintCase):
    """
    Tries to catch common test issues:

    - test files which are never imported
    - double imports (not harmful but useless)
    - nonsense in `tests/__init__` files (e.g. anything other than trivial relative imports)
    """
    def test_check_tests(self):
        checker = InitChecker()

        errors = []
        for manifest in Manifest.all_addon_manifests():
            checker.names.clear()
            p = checker.path = pathlib.Path(manifest.path, 'tests')
            if not p.exists():
                continue

            init = p / '__init__.py'
            assert init.exists(), f"Python test directories must have an init, none found in {p}"

            checker.visit(ast.parse(init.read_bytes(), init))

            for f in p.rglob('test_*.py'):
                # special case of a test file which can't be tested normally
                if f.match("odoo/addons/base/tests/test_uninstall.py"):
                    continue
                checker.names[os.fspath(f.relative_to(p))] -= 1

            for test_path, count in checker.names.items():
                match count:
                    case -1:
                        errors.append(f"Test file {test_path} never imported in {init}")
                    case 0:
                        pass
                    case _:
                        errors.append(f"Test file {test_path} imported multiple times in {init}")

        if errors:
            raise AssertionError("Found test errors:" + "".join(f"\n- {e}" for e in errors))
