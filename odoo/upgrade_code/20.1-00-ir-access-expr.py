"""Rewrite dynamic values of ir.access domains into `*.expr` operators.

The values are moved into strings evaluated by `expr_eval` (see
`_operator_expr_eval` in `odoo/orm/domains.py`), so that the domains can be
parsed with `ast.literal_eval` instead of `safe_eval`.

    [('user_id', '=', user.id)]             => [('user_id', 'in.expr', 'user')]
    [('company_id', 'in', company_ids)]     => [('company_id', 'in.expr', 'companies')]
    [('user_ids', 'in', [user.id, False])]  => [('user_ids', 'in.expr', 'user.ids + [False]')]
    [('user_id', '!=', user.id)]            => ['!', ('user_id', 'in.expr', 'user')]
"""
from __future__ import annotations

import ast
import contextlib
import csv
import io
import logging
import re
import typing

from lxml import etree

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager

_logger = logging.getLogger(__name__)

# names available in the evaluation context of the old domains
NAMES = {
    'user': 'user',
    'website': 'website',
    'company_ids': 'companies',
    'company_id': 'company',
}
# names available in ExprContext
EXPR_NAMES = frozenset(('user', 'company', 'companies', 'partner_id', 'groups', 'website', 'context', 'active'))
# records that always exist, `.id` is never False
NON_EMPTY_RECORDS = frozenset((
    'user', 'company', 'user.company_id',
    'user.partner_id', 'user.commercial_partner_id', 'user.partner_id.commercial_partner_id',
))
OPERATORS = {
    # operator: (new operator, negate)
    '=': ('in.expr', False),
    'in': ('in.expr', False),
    'child_of': ('child_of.expr', False),
    'parent_of': ('parent_of.expr', False),
    '!=': ('in.expr', True),
    'not in': ('in.expr', True),
}
X2MANY_RE = re.compile(r'\w+_ids\.(?!ids$)\w+')


class NoChange(Exception):
    pass


class CannotConvert(Exception):
    pass


def _is_literal(node: ast.AST) -> bool:
    try:
        ast.literal_eval(node)
        return True
    except ValueError:
        return False


def _attr_kind(attr: str) -> str:
    """Guess whether the field is relational from its name."""
    return 'record' if attr.endswith(('_id', '_ids')) else 'scalar'


class DomainConverter:
    """Convert a domain string, keeping its formatting.

    Changes are spliced into the original text using the node offsets.
    """

    def __init__(self):
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self._edits: list[tuple[int, int, str]] = []
        self._line_offsets: list[int] = []

    def transform(self, domain: str) -> str:
        """Return the converted domain or raise NoChange/CannotConvert."""
        self.warnings = []
        self.infos = []
        self._edits = []
        if not domain.strip():
            raise NoChange()
        try:
            ast.literal_eval(domain.strip())
            raise NoChange()
        except (ValueError, SyntaxError, TypeError):
            pass

        stripped = domain.strip()
        prefix = domain[:len(domain) - len(domain.lstrip())]
        suffix = domain[len(domain.rstrip()):]
        source = stripped.encode()  # offsets are in utf-8 bytes
        self._line_offsets = [0]
        for line in source.splitlines(keepends=True):
            self._line_offsets.append(self._line_offsets[-1] + len(line))

        node = ast.parse(stripped, mode='eval').body
        self._visit_domain(node)
        if not self._edits:
            raise NoChange()

        for start, end, text in sorted(self._edits, reverse=True):
            source = source[:start] + text.encode() + source[end:]
        result = source.decode()
        try:
            ast.literal_eval(result)
        except (ValueError, SyntaxError) as e:
            raise CannotConvert(f"result is not a literal: {result!r}") from e
        return prefix + result + suffix

    # offsets

    def _start(self, node):
        return self._line_offsets[node.lineno - 1] + node.col_offset

    def _end(self, node):
        return self._line_offsets[node.end_lineno - 1] + node.end_col_offset

    def _replace(self, node, text):
        self._edits.append((self._start(node), self._end(node), text))

    def _insert(self, node, text):
        start = self._start(node)
        self._edits.append((start, start, text))

    # domain

    def _visit_domain(self, node):
        if not isinstance(node, (ast.List, ast.Tuple)):
            raise CannotConvert(f"not a list: {ast.unparse(node)}")
        for item in node.elts:
            if isinstance(item, ast.Constant) and item.value in ('|', '&', '!'):
                continue
            self._visit_condition(item)

    def _visit_condition(self, node):
        if not (
            isinstance(node, (ast.List, ast.Tuple))
            and len(node.elts) == 3
            and _is_literal(node.elts[0])
            and isinstance(node.elts[1], ast.Constant)
        ):
            if _is_literal(node):
                return
            raise CannotConvert(f"invalid condition: {ast.unparse(node)}")
        _field_node, op_node, value_node = node.elts
        operator = op_node.value
        if _is_literal(value_node):
            return
        if operator in ('any', 'not any', 'any!', 'not any!'):
            self._visit_domain(value_node)
            return
        if operator not in OPERATORS:
            raise CannotConvert(f"unsupported operator {operator!r}: {ast.unparse(node)}")
        new_operator, negate = OPERATORS[operator]
        expr = self._convert_value(value_node)
        if negate:
            self._insert(node, "'!', ")
        self._replace(op_node, repr(new_operator))
        self._replace(value_node, repr(expr))

    # values

    def _convert_value(self, node) -> str:
        expr, kind = self._expr(node)
        if kind == 'scalar':
            # field of a singleton record, e.g. user.login
            if expr.rpartition('.')[0] not in NON_EMPTY_RECORDS:
                raise CannotConvert(f"unsupported value: {ast.unparse(node)}")
            expr = f"[{expr}]"
        if X2MANY_RE.search(expr):
            self.infos.append(f"traversal of x2many: {expr}")
        self._check_expr(expr)
        return expr

    def _expr(self, node) -> tuple[str, str]:
        """Return the expression and its kind: 'record', 'list' or 'scalar'."""
        match node:
            case ast.Constant(value=value):
                return repr(value), 'scalar'
            case ast.Name(id=name) if name in NAMES:
                return NAMES[name], 'record'
            case ast.Attribute(value=ast.Attribute(attr='env'), attr=('companies' | 'company') as attr):
                base, kind = self._expr(node.value.value)
                if base != 'user' or kind != 'record':
                    raise CannotConvert(f"unsupported env access: {ast.unparse(node)}")
                return attr, 'record'
            case ast.Attribute(value=value, attr='id'):
                base, kind = self._expr(value)
                if kind != 'record':
                    raise CannotConvert(f"unsupported id access: {ast.unparse(node)}")
                if base not in NON_EMPTY_RECORDS:
                    self.warnings.append(
                        f"{ast.unparse(node)} may be False, the new domain does not match empty values",
                    )
                return base, 'record'
            case ast.Attribute(value=value, attr='ids'):
                base, kind = self._expr(value)
                if kind != 'record':
                    raise CannotConvert(f"unsupported ids access: {ast.unparse(node)}")
                return f"{base}.ids", 'list'
            case ast.Attribute(value=value, attr=attr):
                base, kind = self._expr(value)
                if kind != 'record':
                    raise CannotConvert(f"unsupported attribute: {ast.unparse(node)}")
                return f"{base}.{attr}", _attr_kind(attr)
            case ast.Call(
                func=ast.Attribute(value=value, attr='mapped'),
                args=[ast.Constant(value=str() as path)],
                keywords=[],
            ):
                base, kind = self._expr(value)
                if kind != 'record' or _attr_kind(path.rpartition('.')[2]) != 'record':
                    # expr_eval cannot map non-relational fields on multiple records
                    raise CannotConvert(f"unsupported mapped: {ast.unparse(node)}")
                return f"{base}.{path}", 'record'
            case ast.List(elts=elts) | ast.Tuple(elts=elts):
                parts = []
                constants = []
                for elt in elts:
                    if isinstance(elt, ast.Constant):
                        constants.append(elt.value)
                    elif isinstance(elt, ast.Starred):
                        parts.append(self._as_list(elt.value))
                    else:
                        parts.append(self._as_list(elt))
                if constants:
                    parts.append(repr(constants))
                if not parts:
                    return '[]', 'list'
                return ' + '.join(parts), 'list'
            case ast.BinOp(op=ast.Add(), left=left, right=right):
                return f"{self._as_list(left)} + {self._as_list(right)}", 'list'
        raise CannotConvert(f"unsupported expression: {ast.unparse(node)}")

    def _as_list(self, node) -> str:
        expr, kind = self._expr(node)
        if kind == 'record':
            return f"{expr}.ids"
        if kind == 'scalar':
            return f"[{expr}]"
        return expr

    def _check_expr(self, expr: str):
        """Check that the expression is supported by expr_eval and ExprContext."""
        for node in ast.walk(ast.parse(expr, mode='eval')):
            if isinstance(node, ast.Name) and node.id not in EXPR_NAMES:
                raise CannotConvert(f"unknown name {node.id!r} in {expr!r}")
            if not isinstance(node, (
                ast.Expression, ast.Name, ast.Attribute, ast.Load, ast.Constant,
                ast.List, ast.BinOp, ast.Add,
            )):
                raise CannotConvert(f"unsupported syntax {type(node).__name__} in {expr!r}")


def _xml_escape(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _convert(converter: DomainConverter, domain: str, where: str) -> str | None:
    try:
        new_domain = converter.transform(domain)
    except NoChange:
        return None
    except (CannotConvert, SyntaxError) as e:
        _logger.warning("%s: cannot convert domain, migrate manually: %s", where, e)
        return None
    for message in converter.warnings:
        _logger.warning("%s: %s", where, message)
    for message in converter.infos:
        _logger.info("%s: %s; consider a searchable computed field", where, message)
    return new_domain


def upgrade_csv(file, converter: DomainConverter):
    content = file.content
    reader = csv.reader(io.StringIO(content, newline=''))
    header = next(reader, None)
    if not header:
        return
    domain_index = next((i for i, name in enumerate(header) if name.split(':')[0] == 'domain'), None)
    if domain_index is None:
        return
    replacements = {}
    for row in reader:
        if len(row) <= domain_index or (domain := row[domain_index]) in replacements:
            continue
        new_domain = _convert(converter, domain, f"{file.path}:{row[0]}")
        if new_domain is None:
            continue
        old_cell = '"' + domain.replace('"', '""') + '"'
        if old_cell not in content:
            _logger.warning("%s:%s: domain not found in file", file.path, row[0])
            continue
        replacements[domain] = new_domain
    for domain, new_domain in replacements.items():
        old_cell = '"' + domain.replace('"', '""') + '"'
        new_cell = '"' + new_domain.replace('"', '""') + '"'
        content = content.replace(old_cell, new_cell)
    file.content = content


def upgrade_xml(file, converter: DomainConverter):
    content = file.content
    if 'ir.access' not in content:
        return
    try:
        tree = etree.parse(io.BytesIO(content.encode()))
    except etree.XMLSyntaxError as e:
        _logger.info("Failed to parse the file %s: %s", file.path, e)
        return
    for field in tree.iterfind(".//record[@model='ir.access']/field[@name='domain']"):
        domain = field.text
        if not domain or len(field):
            continue
        record_id = field.getparent().get('id')
        new_domain = _convert(converter, domain, f"{file.path}:{record_id}")
        if new_domain is None:
            continue
        for old_text in (_xml_escape(domain), domain.replace('&', '&amp;').replace('<', '&lt;')):
            if old_text in content:
                content = content.replace(old_text, _xml_escape(new_domain))
                break
        else:
            _logger.warning("%s:%s: domain not found in file", file.path, record_id)
    file.content = content


def upgrade(file_manager: FileManager):
    converter = DomainConverter()
    files = [
        file for file in file_manager
        if file.path.name == 'ir.access.csv'
        or (file.path.suffix == '.xml' and file.path.parent.name in ('data', 'security'))
    ]
    for fileno, file in enumerate(files, start=1):
        if file.path.suffix == '.csv':
            upgrade_csv(file, converter)
        else:
            upgrade_xml(file, converter)
        file_manager.print_progress(fileno, len(files))


def test(domain, result):
    output = DomainConverter().transform(domain)
    assert output == result, f"Failed to convert {domain!r}; got {output!r} instead of {result!r}"


def test_fail(domain):
    try:
        DomainConverter().transform(domain)
    except CannotConvert:
        return
    raise AssertionError(f"Should not convert {domain!r}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    test("[('user_id', '=', user.id)]", "[('user_id', 'in.expr', 'user')]")
    test("[('company_id', 'in', company_ids)]", "[('company_id', 'in.expr', 'companies')]")
    test("['|', ('company_id', '=', False), ('company_id', 'parent_of', company_ids)]",
         "['|', ('company_id', '=', False), ('company_id', 'parent_of.expr', 'companies')]")
    test("[('user_ids', 'in', [user.id, False])]", "[('user_ids', 'in.expr', 'user.ids + [False]')]")
    test("[('company_id', 'in', [False, *company_ids])]", "[('company_id', 'in.expr', 'companies.ids + [False]')]")
    test("[('user_id', '!=', user.id)]", "['!', ('user_id', 'in.expr', 'user')]")
    test("[('partner_id', 'child_of', user.partner_id.commercial_partner_id.id)]",
         "[('partner_id', 'child_of.expr', 'user.partner_id.commercial_partner_id')]")
    test("[('country_id', 'in', user.env.companies.mapped('country_id').ids + [False])]",
         "[('country_id', 'in.expr', 'companies.country_id.ids + [False]')]")
    test("[('company_id', 'in', [False, website.company_id.id])]",
         "[('company_id', 'in.expr', 'website.company_id.ids + [False]')]")
    test("[('group_ids', 'in', user.all_group_ids.ids)]", "[('group_ids', 'in.expr', 'user.all_group_ids.ids')]")
    test("[('a', 'any', [('partner_id', '=', user.partner_id.id), ('x', '=', 1)])]",
         "[('a', 'any', [('partner_id', 'in.expr', 'user.partner_id'), ('x', '=', 1)])]")
    # formatting is kept
    test("""[
        '|',
            ('user_id', '=', user.id),  # comment
            ('x', '=', 'é'), ('y', '=', user.id),
    ]""", """[
        '|',
            ('user_id', 'in.expr', 'user'),  # comment
            ('x', '=', 'é'), ('y', 'in.expr', 'user'),
    ]""")
    test_fail("[('x', '=', user.env.ref('base.main_company').id)]")
    test_fail("[('x', '>', user.id)]")
    test_fail("[('x', 'in', user.env.companies.mapped('country_code') + [False])]")
    test("[('login', '=', user.login)]", "[('login', 'in.expr', '[user.login]')]")
    test_fail("[('x', '=', user.employee_id.name)]")
    test_fail("[('x', '=', time.strftime('%Y'))]")
    with contextlib.suppress(NoChange):
        DomainConverter().transform("[('x', '=', 1)]")
        raise AssertionError("literal domain should not change")  # noqa: EM101
    _logger.info("All tests passed")
