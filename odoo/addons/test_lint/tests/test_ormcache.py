# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import itertools
import logging

from odoo.tests import tagged
from odoo.tools.misc import file_open

from . import lint_case

_logger = logging.getLogger(__name__)


class OrmcacheParamsChecker(lint_case.NodeVisitor):
    @staticmethod
    def _matches_ormcache(node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                return node.func.attr == 'ormcache'
            if isinstance(node.func, ast.Name):
                return node.func.id == 'ormcache'
        return False

    @staticmethod
    def _get_expression_names(expr):
        # 'frozenset(filtered_combination.ids)' -> {'filtered_combination', 'frozenset'}
        expression = ast.parse(expr, mode='eval')
        return {
            child.id
            for child in ast.walk(expression)
            if isinstance(child, ast.Name)
        }

    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list:
            if not self._matches_ormcache(decorator):
                continue

            cache_args = [
                arg.value
                for arg in decorator.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            ]
            cached_param_names = set().union(*(self._get_expression_names(expr) for expr in cache_args))
            method_param_names = [
                arg.arg
                for arg in itertools.chain(node.args.posonlyargs, node.args.args, node.args.kwonlyargs)
                if arg.arg not in ('self', 'cls') and not (arg.arg.startswith('_') and arg in node.args.kwonlyargs)
            ]
            missing_params = [
                param_name
                for param_name in method_param_names
                if param_name not in cached_param_names
            ]
            if missing_params:
                yield node, tuple(missing_params)
            return


@tagged('at_install', '-post_install')
class TestOrmCacheDecoratorWarnings(lint_case.LintCase):
    def test_missing_method_params_in_cache_key_warns(self):
        checker = OrmcacheParamsChecker()
        warnings = []

        for path in self.iter_module_files('*.py'):
            with file_open(path, 'rb') as f:
                source = f.read()
            if b'ormcache' not in source:
                continue
            tree = ast.parse(source, path)
            warnings.extend(
                (path, node.lineno, node.name, missing_params)
                for node, missing_params in checker.visit(tree)
            )

        if warnings:
            details = "\n".join(
                f"{missing_params} for {func_name} in {path}:{lineno}"
                for path, lineno, func_name, missing_params in sorted(warnings)
            )
            _logger.warning(
                "ormcache key is missing method parameters.\n"
                "If a parameter is intentionally unused in the cache key, it must be kw-only and prefixed with '_' (e.g. def method(..., *, _kwarg=None): ...) to skip this check.\n"
                "%s",
                details,
            )
