# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import itertools

from .common import LintCase


class OrmcacheParamsChecker(ast.NodeVisitor):
    def add_error(self, node, missing_params):
        pass

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
                self.add_error(node, tuple(missing_params))
            return


class OnchangeChecker(ast.NodeVisitor):
    def add_error(self, node):
        pass

    def matches_onchange(self, node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                return node.func.attr == 'onchange'
            if isinstance(node.func, ast.Name):
                return node.func.id == 'onchange'
        return False

    def visit_FunctionDef(self, node):
        walker = ast.walk(node) if any(map(self.matches_onchange, node.decorator_list)) else []
        for n in walker:
            if isinstance(n, ast.Constant) and n.value == 'domain':
                self.add_error(n)
                # can stop at the first match: an @onchange function either mentions
                # domains or does not
                break


class TestOrmCacheDecoratorWarnings(LintCase):
    def test_missing_method_params_in_cache_key_warns(self):
        checker = OrmcacheParamsChecker()
        errors = []

        for path in self.iter_module_files('*.py'):
            checker.add_error = lambda node, missing_params: errors.append(
                f"{missing_params} for {node.name} in {path}:{node.lineno}"
            )
            self.visit_python_file(path, checker, should_parse=lambda source: b'ormcache' in source)

        if errors:
            errors[:0] = [
                "ormcache key is missing method parameters.",
                "If a parameter is intentionally unused in the cache key, it must be kw-only and prefixed with '_' (e.g. def method(..., *, _kwarg=None): ...) to skip this check.",
            ]
            self.fail("\n".join(errors))

    def test_forbid_domains_in_onchanges(self):
        """ Dynamic domains (returning a domain from an onchange) are deprecated
        and should not be used in "standard" Odoo anymore
        """
        checker = OnchangeChecker()
        rs = []
        for path in self.iter_module_files('*.py'):
            checker.add_error = lambda node: rs.append(f"{path}:{node.lineno}")
            self.visit_python_file(path, checker, should_parse=lambda source: b'onchange' in source and b'domain' in source)

        if rs:
            rs.insert(0, "probable domains in onchanges at:")
            self.fail("\n- ".join(rs))
