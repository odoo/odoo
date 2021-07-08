import ast
import itertools
import os

from . import lint_case


class OnchangeChecker(lint_case.NodeVisitor):
    def matches_onchange(self, node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                return node.func.attr == 'onchange'
            if isinstance(node.func, ast.Name):
                return node.func.id == 'onchange'
        return False

    def visit_FunctionDef(self, node):
        walker = ast.walk(node) if any(map(self.matches_onchange, node.decorator_list)) else []
        # can stop at the first match: an @onchange function either mentions
        # domains or does not
        return itertools.islice((
            n for n in walker
            if isinstance(n, getattr(ast, 'Str', type(None))) and n.s == 'domain'
            or isinstance(n, getattr(ast, 'Constant', type(None))) and n.value == 'domain'
        ), 1)


class TestOnchangeDomains(lint_case.LintCase):
    """ Would ideally have been a pylint module but that's slow as molasses
    (takes minutes to run, and can blow up entirely depending on the pylint
    version)
    """
    def test_forbid_domains_in_onchanges(self):
        """ Dynamic domains (returning a domain from an onchange) are deprecated
        and should not be used in "standard" Odoo anymore
        """
        checker = OnchangeChecker()
        rs = []
        for path in self.iter_module_files('*.py'):
            with open(path, 'rb') as f:
                t = ast.parse(f.read(), path)
            rs.extend(zip(itertools.repeat(os.path.relpath(path)), checker.visit(t)))

        rs.sort(key=lambda t: t[0])
        assert not rs, "probable domains in onchanges at\n" + '\n'.join(
            "- %s:%d" % (path, node.lineno)
            for path, node in rs
        )
