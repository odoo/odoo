# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Derive SQL for non-stored computed fields.

This module is deliberately built as a small pipeline:

* parse a compute method into a tiny intermediate shape;
* lower ordinary Python expressions to SQL;
* recognize SQL/projection computes;
* keep exceptional business semantics in one adapter catalog.

The adapter catalog exists because a few current computes do not contain their
business formula in Python at all: they select ``query.table.<same field>`` or
delegate to ORM/report helpers.  Those cases are supported, but isolated so they
can be replaced by more general primitives without touching the expression
lowerer.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import logging
import re
import textwrap
from collections.abc import Callable
from typing import Any

_logger = logging.getLogger(__name__)


class _UnsupportedNode(Exception):
    """Raised when a compute cannot be represented safely as SQL."""


def _S():
    from odoo.tools import SQL
    return SQL


_TRANSPARENT_RECORDSET_METHODS = {'sudo', 'with_context', 'with_company'}
_EXPENSIVE_RE = re.compile(r'\bEXISTS\s*\([^)]*\)', re.IGNORECASE | re.DOTALL)


# ---------------------------------------------------------------------------
# AST and constant helpers
# ---------------------------------------------------------------------------

def _source_funcdef(method) -> ast.FunctionDef:
    try:
        source = textwrap.dedent(inspect.getsource(getattr(method, '__wrapped__', method)))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError) as exc:
        raise _UnsupportedNode(f"Cannot parse compute method: {exc}") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise _UnsupportedNode("No function body found")


def _unroll(node: ast.AST) -> tuple[list[str], ast.AST]:
    chain: list[str] = []
    while True:
        if isinstance(node, ast.Attribute):
            chain.append(node.attr)
            node = node.value
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _TRANSPARENT_RECORDSET_METHODS
        ):
            node = node.func.value
        else:
            break
    chain.reverse()
    return chain, node


def _const(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    raise _UnsupportedNode(f"Expected constant, got {ast.unparse(node)!r}")


def _const_seq(node: ast.AST) -> list[Any]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_const(elt) for elt in node.elts]
    return [_const(node)]


def _is_env_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in {'self', 'fields', 'date'}
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Attribute):
        return _is_env_expr(node.value)
    if isinstance(node, ast.Subscript):
        return _is_env_expr(node.value) and isinstance(node.slice, ast.Constant)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr not in {
            *_TRANSPARENT_RECORDSET_METHODS,
            'browse',
            'get',
            '_get_main_company',
            '_get_definition_for_property_field',
            '_get_definition_id_for_property_field',
        }:
            return False
        return (
            _is_env_expr(node.func.value)
            and all(_is_env_expr(arg) for arg in node.args)
            and all(kw.arg and _is_env_expr(kw.value) for kw in node.keywords)
        )
    return False


def _eval_env(model, node: ast.AST):
    from datetime import date
    from odoo import fields
    if isinstance(node, ast.Name):
        if node.id == 'self':
            return model
        if node.id == 'fields':
            return fields
        if node.id == 'date':
            return date
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Attribute):
        return getattr(_eval_env(model, node.value), node.attr)
    if isinstance(node, ast.Subscript):
        return _eval_env(model, node.value)[_const(node.slice)]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        receiver = _eval_env(model, node.func.value)
        args = [_eval_env(model, arg) for arg in node.args]
        kwargs = {kw.arg: _eval_env(model, kw.value) for kw in node.keywords if kw.arg}
        return getattr(receiver, node.func.attr)(*args, **kwargs)
    raise _UnsupportedNode(f"Not a setup-time expression: {ast.unparse(node)!r}")


def _constant_sql(value):
    SQL = _S()
    if hasattr(value, '_name') and hasattr(value, 'ids'):
        if len(value) > 1:
            raise _UnsupportedNode("Multi-record constant")
        value = value.id
    return SQL('%s', value)


def _constant_chain_sql(value, chain: list[str]):
    if hasattr(value, '_name') and hasattr(value, 'ids') and chain:
        from odoo.orm.query import Query
        SQL = _S()
        if len(value) > 1:
            raise _UnsupportedNode("Multi-record constant")
        query = Query(value)
        query.add_where(SQL("%s = %s", query.table.id, value.id))
        sql = query.table
        for index, fname in enumerate(chain):
            if fname == 'id' and index:
                continue
            sql = sql[fname]
        return SQL("(%s)", query.select(sql))
    for attr in chain:
        value = getattr(value, attr)
    return _constant_sql(value)


def _field_type_for_chain(model, chain: list[str]) -> str:
    for index, fname in enumerate(chain):
        field = model._fields.get(fname)
        if not field:
            return 'unknown'
        if index == len(chain) - 1:
            return field.type
        if not field.comodel_name:
            return 'unknown'
        model = model.env[field.comodel_name]
    return 'unknown'


def _make_attr(value: ast.expr, chain: list[str]) -> ast.expr:
    for attr in chain:
        value = ast.Attribute(value=value, attr=attr, ctx=ast.Load())
    return ast.fix_missing_locations(value)


class _NameRewriter(ast.NodeTransformer):
    def __init__(self, old_name, new_name):
        self.old_name = old_name
        self.new_name = new_name

    def visit_Name(self, node):
        if node.id == self.old_name:
            return ast.copy_location(ast.Name(id=self.new_name, ctx=node.ctx), node)
        return node


def _rewrite_name(node, old_name, new_name):
    return ast.fix_missing_locations(_NameRewriter(old_name, new_name).visit(node))


def _same_expr(left: ast.AST, right: ast.AST) -> bool:
    return ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)


def _is_record_id(node: ast.AST, record_var: str) -> bool:
    chain, base = _unroll(node)
    return isinstance(base, ast.Name) and base.id == record_var and chain in (['id'], ['_origin', 'id'])


# ---------------------------------------------------------------------------
# Intermediate representation
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class _EnvConst:
    node: ast.AST


@dataclasses.dataclass(frozen=True)
class _FieldSQL:
    field_name: str


@dataclasses.dataclass(frozen=True)
class _MethodSQL:
    method_name: str


@dataclasses.dataclass(frozen=True)
class _RecordVariant:
    node: ast.AST


@dataclasses.dataclass(frozen=True)
class _Spec:
    record_var: str
    bindings: dict[str, Any]
    target: ast.expr


@dataclasses.dataclass
class _Ctx:
    record_var: str
    model: Any
    table: Any
    bindings: dict[str, Any]
    target_type: str | None = None
    depth: int = 0


# ---------------------------------------------------------------------------
# Expression lowering
# ---------------------------------------------------------------------------

class _Compiler:
    _BINOPS = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/', ast.FloorDiv: '/', ast.Mod: '%'}
    _CMPOPS = {ast.Eq: '=', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>='}
    _STRING_METHODS = {
        'upper': 'UPPER(%s)',
        'lower': 'LOWER(%s)',
        'strip': 'TRIM(%s)',
        'lstrip': 'LTRIM(%s)',
        'rstrip': 'RTRIM(%s)',
    }

    def __init__(self, ctx: _Ctx):
        self.ctx = ctx
        self._expanding: set[str] = set()
        self._value_depth = 0

    def sql(self, node: ast.expr):
        method = getattr(self, f'visit_{type(node).__name__}', None)
        if method is None:
            raise _UnsupportedNode(f"Unsupported expression {type(node).__name__}: {ast.unparse(node)!r}")
        return method(node)

    def value_sql(self, node: ast.expr):
        self._value_depth += 1
        try:
            return self.sql(node)
        finally:
            self._value_depth -= 1

    def bool_sql(self, node: ast.expr):
        old_depth = self._value_depth
        self._value_depth = 0
        try:
            if isinstance(node, ast.BoolOp):
                return self._boolop(node, bool_mode=True)
            sql = self.sql(node)
            if isinstance(node, (ast.Compare, ast.UnaryOp)):
                return sql
            return self._coerce_bool(node, sql)
        finally:
            self._value_depth = old_depth

    def visit_Constant(self, node):
        SQL = _S()
        if node.value is None:
            return SQL('NULL')
        if isinstance(node.value, bool):
            if node.value is False and self._value_depth and self.ctx.target_type != 'boolean':
                return SQL('NULL')
            return SQL('TRUE' if node.value else 'FALSE')
        return SQL('%s', node.value)

    def visit_List(self, node):
        return [_const(elt) for elt in node.elts]

    visit_Tuple = visit_List
    visit_Set = visit_List

    def visit_Name(self, node):
        if node.id in ('True', 'False', 'None'):
            return self.visit_Constant(ast.Constant({'True': True, 'False': False, 'None': None}[node.id]))
        if node.id not in self.ctx.bindings:
            raise _UnsupportedNode(f"Unresolved name {node.id!r}")
        binding = self.ctx.bindings[node.id]
        if isinstance(binding, _EnvConst):
            return _constant_sql(_eval_env(self.ctx.model, binding.node))
        if isinstance(binding, _FieldSQL):
            return self.ctx.table[binding.field_name]
        if isinstance(binding, _MethodSQL):
            return getattr(self.ctx.model, binding.method_name)(self.ctx.table)
        if isinstance(binding, _RecordVariant):
            return self.ctx.table._with_model(_eval_env(self.ctx.model, binding.node)).id
        if isinstance(binding, ast.expr):
            if node.id in self._expanding:
                raise _UnsupportedNode(f"Recursive binding {node.id!r}")
            self._expanding.add(node.id)
            try:
                return self.sql(binding)
            finally:
                self._expanding.remove(node.id)
        return _constant_sql(binding)

    def visit_Attribute(self, node):
        try:
            if _is_env_expr(node):
                return _constant_sql(_eval_env(self.ctx.model, node))
        except Exception:
            pass
        chain, base = _unroll(node)
        if isinstance(base, ast.BoolOp) and isinstance(base.op, ast.Or) and chain:
            return _S()('COALESCE(%s)', _S()(', ').join(self.value_sql(_make_attr(value, chain)) for value in base.values))
        if isinstance(base, ast.Name) and base.id == self.ctx.record_var:
            return self._field_chain_sql(self.ctx.model, self.ctx.table, chain, node)
        if isinstance(base, ast.Name) and base.id in self.ctx.bindings:
            binding = self.ctx.bindings[base.id]
            if isinstance(binding, _EnvConst):
                return _constant_chain_sql(_eval_env(self.ctx.model, binding.node), chain)
            if isinstance(binding, _RecordVariant):
                table = self.ctx.table._with_model(_eval_env(self.ctx.model, binding.node))
                return self._field_chain_sql(table._model, table, chain, node)
            if isinstance(binding, ast.expr):
                return self.sql(_make_attr(binding, chain))
            return _constant_chain_sql(binding, chain)
        raise _UnsupportedNode(f"Unsupported attribute: {ast.unparse(node)!r}")

    def _field_chain_sql(self, model, table, chain: list[str], node):
        if chain and chain[0] == '_origin':
            chain = chain[1:]
        if not chain:
            return table.id
        field = model._fields.get(chain[0])
        if field and field.type in ('one2many', 'many2many'):
            if len(chain) == 1:
                return self._relation_exists_sql(model, table, chain[0])
            if len(chain) == 2:
                return self._relation_field_sql(model, table, chain[0], chain[1])
        sql = table
        for index, fname in enumerate(chain):
            if fname == 'id' and index:
                continue
            sql = sql[fname]
        return sql

    def _relation_exists_sql(self, model, table, field_name):
        SQL = _S()
        field = model._fields[field_name]
        if field.type == 'many2many':
            return SQL(
                "EXISTS (SELECT 1 FROM %s rel WHERE rel.%s = %s)",
                SQL.identifier(field.relation),
                SQL.identifier(field.column1),
                table.id,
            )
        comodel = model.env[field.comodel_name]
        return SQL(
            "EXISTS (SELECT 1 FROM %s child WHERE child.%s = %s)",
            SQL.identifier(comodel._table),
            SQL.identifier(field.inverse_name),
            table.id,
        )

    def _relation_field_sql(self, model, table, field_name, target_name):
        SQL = _S()
        field = model._fields[field_name]
        comodel = model.env[field.comodel_name]
        if field.type == 'many2many':
            return SQL(
                """(
                    SELECT child.%s
                      FROM %s rel
                      JOIN %s child ON child.id = rel.%s
                     WHERE rel.%s = %s
                     LIMIT 1
                )""",
                SQL.identifier(target_name),
                SQL.identifier(field.relation),
                SQL.identifier(comodel._table),
                SQL.identifier(field.column2),
                SQL.identifier(field.column1),
                table.id,
            )
        return SQL(
            "(SELECT child.%s FROM %s child WHERE child.%s = %s LIMIT 1)",
            SQL.identifier(target_name),
            SQL.identifier(comodel._table),
            SQL.identifier(field.inverse_name),
            table.id,
        )

    def visit_BinOp(self, node):
        op = self._BINOPS.get(type(node.op))
        if op is None:
            raise _UnsupportedNode(f"Unsupported operator {type(node.op).__name__}")
        return _S()(f'(%s {op} %s)', self.sql(node.left), self.sql(node.right))

    def visit_Compare(self, node):
        SQL = _S()
        if len(node.ops) != 1:
            raise _UnsupportedNode("Chained comparisons are not supported")
        op = node.ops[0]
        right_node = node.comparators[0]
        if isinstance(op, (ast.In, ast.NotIn)):
            neg = isinstance(op, ast.NotIn)
            if sql := self._record_in_recordset(node.left, right_node, neg):
                return sql
            if sql := self._many2many_contains(node.left, right_node, neg):
                return sql
            left = self.sql(node.left)
            try:
                right = self.sql(right_node)
            except _UnsupportedNode:
                right = None
            if isinstance(right, list):
                values = right
            elif right is not None:
                return SQL('(%s %s %s)', left, SQL('NOT IN' if neg else 'IN'), right)
            else:
                values = _const_seq(right_node)
            if not values:
                return SQL('TRUE' if neg else 'FALSE')
            return SQL('(%s %s %s)', left, SQL('NOT IN' if neg else 'IN'), SQL('%s', tuple(values)))
        left = self.sql(node.left)
        right = self.sql(right_node)
        sql_op = self._CMPOPS.get(type(op))
        if sql_op is None:
            raise _UnsupportedNode(f"Unsupported comparison {type(op).__name__}")
        if isinstance(right_node, ast.Constant) and right_node.value is None:
            return SQL('(%s IS NULL)', left) if sql_op == '=' else SQL('(%s IS NOT NULL)', left)
        return SQL(f'(%s {sql_op} %s)', left, right)

    def _record_in_recordset(self, left, right, neg=False):
        if not (isinstance(left, ast.Name) and left.id == self.ctx.record_var):
            return None
        if not isinstance(right, ast.Name):
            return None
        binding = self.ctx.bindings.get(right.id)
        if not isinstance(binding, _EnvConst):
            return None
        recordset = _eval_env(self.ctx.model, binding.node)
        if not hasattr(recordset, '_name') or recordset._name != self.ctx.model._name:
            return None
        return _S()('(%s %s %s)', self.ctx.table.id, _S()('NOT IN' if neg else 'IN'), _S()('%s', tuple(recordset.ids) or (None,)))

    def _many2many_contains(self, left, right, neg=False):
        chain, base = _unroll(right)
        if not (isinstance(base, ast.Name) and base.id == self.ctx.record_var and len(chain) == 1):
            return None
        field = self.ctx.model._fields.get(chain[0])
        if not field or field.type != 'many2many':
            return None
        SQL = _S()
        return SQL(
            "%sEXISTS (SELECT 1 FROM %s rel WHERE rel.%s = %s AND rel.%s = %s)",
            SQL('NOT ') if neg else SQL(''),
            SQL.identifier(field.relation),
            SQL.identifier(field.column1),
            self.ctx.table.id,
            SQL.identifier(field.column2),
            self.sql(left),
        )

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.And) and self.ctx.target_type in {'many2one', 'integer', 'float', 'monetary', 'char', 'text', 'selection', 'date', 'datetime'}:
            return _S()(
                'CASE WHEN %s THEN %s ELSE NULL END',
                _S()(' AND ').join(self.bool_sql(value) for value in node.values[:-1]),
                self.value_sql(node.values[-1]),
            )
        if isinstance(node.op, ast.Or) and self.ctx.target_type in {'many2one', 'integer', 'float', 'monetary', 'char', 'text', 'selection', 'date', 'datetime'}:
            return _S()('COALESCE(%s)', _S()(', ').join(self.value_sql(value) for value in node.values))
        return self._boolop(node, bool_mode=False)

    def _boolop(self, node, bool_mode):
        SQL = _S()
        is_and = isinstance(node.op, ast.And)
        parts = []
        for value in node.values:
            pyval = self._pyval(value)
            if pyval is not None:
                if is_and and pyval is False:
                    return SQL('FALSE')
                if not is_and and pyval is True:
                    return SQL('TRUE')
            else:
                parts.append(value)
        if not parts:
            return SQL('TRUE' if is_and else 'FALSE')
        if len(parts) == 1:
            return self.bool_sql(parts[0]) if bool_mode else self.sql(parts[0])
        sep = SQL(' AND ' if is_and else ' OR ')
        return SQL('(%s)', sep.join(self.bool_sql(part) for part in parts))

    def _pyval(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and isinstance(self.ctx.bindings.get(node.id), ast.Constant):
            return self.ctx.bindings[node.id].value
        return None

    def visit_UnaryOp(self, node):
        SQL = _S()
        if isinstance(node.op, ast.Not):
            return SQL('(NOT %s)', self.bool_sql(node.operand))
        if isinstance(node.op, ast.USub):
            return SQL('(-%s)', self.sql(node.operand))
        if isinstance(node.op, ast.UAdd):
            return self.sql(node.operand)
        raise _UnsupportedNode(f"Unsupported unary operator {type(node.op).__name__}")

    def visit_IfExp(self, node):
        if coalesced := self._coalesced_len(node):
            return coalesced
        return _S()(
            'CASE WHEN %s THEN %s ELSE %s END',
            self.bool_sql(node.test),
            self.value_sql(node.body),
            self.value_sql(node.orelse),
        )

    def _coalesced_len(self, node):
        if not (
            isinstance(node.body, ast.Call)
            and isinstance(node.body.func, ast.Name)
            and node.body.func.id == 'len'
            and len(node.body.args) == 1
            and isinstance(node.orelse, ast.Constant)
            and node.orelse.value in (0, False, None)
            and _same_expr(node.test, node.body.args[0])
        ):
            return None
        return _S()('COALESCE(LENGTH(%s), 0)', self.sql(node.body.args[0]))

    def visit_Subscript(self, node):
        SQL = _S()
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == 'split'
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == 0
        ):
            separator = node.value.args[0] if node.value.args else ast.Constant(None)
            return SQL("SPLIT_PART(%s, %s, 1)", self.sql(node.value.func.value), self.sql(separator))
        if (
            isinstance(node.slice, ast.Slice)
            and node.slice.lower is None
            and isinstance(node.slice.upper, ast.Constant)
            and node.slice.step is None
        ):
            return SQL("SUBSTRING(%s, 1, %s)", self.sql(node.value), node.slice.upper.value)
        raise _UnsupportedNode(f"Unsupported subscript: {ast.unparse(node)!r}")

    def visit_Call(self, node):
        from datetime import date
        from odoo import fields
        SQL = _S()
        try:
            if _is_env_expr(node):
                return _constant_sql(_eval_env(self.ctx.model, node))
        except Exception:
            pass
        if isinstance(node.func, ast.Attribute):
            chain, base = _unroll(node.func)
            if isinstance(base, ast.Name) and base.id == 'fields' and chain == ['Date', 'context_today']:
                return SQL('%s', fields.Date.context_today(self.ctx.model))
            if isinstance(base, ast.Name) and base.id == 'date' and chain == ['today'] and not node.args:
                return SQL('%s', date.today())
            if node.func.attr == 'is_zero' and len(node.args) == 1:
                try:
                    _eval_env(self.ctx.model, node.func.value)
                except Exception:
                    pass
                else:
                    return SQL('(%s = 0)', self.sql(node.args[0]))
            if len(chain) == 1 and chain[0] == 'browse' and len(node.args) == 1 and (
                isinstance(base, ast.Name) and base.id == 'self' or _is_env_expr(base)
            ):
                return self.sql(node.args[0])
            if isinstance(base, ast.Name) and base.id == self.ctx.record_var and len(chain) == 1:
                return self._inline_record_method(chain[0], node.args, node.keywords)
            if (isinstance(base, ast.Name) and base.id == 'self' or _is_env_expr(base)) and len(chain) == 1:
                return self._inline_model_method(base, chain[0], node.args, node.keywords)
            if len(chain) == 1:
                return self._string_method(base, chain[0], node.args)
        if isinstance(node.func, ast.Name):
            return self._builtin(node)
        raise _UnsupportedNode(f"Unsupported call: {ast.unparse(node)!r}")

    def _builtin(self, node):
        SQL = _S()
        name = node.func.id
        if name in {'str', 'int', 'float'}:
            cast = {'str': 'text', 'int': 'integer', 'float': 'float8'}[name]
            return SQL('(%s::%s)', self.sql(node.args[0]), SQL(cast))
        if name == 'bool':
            return self.bool_sql(node.args[0])
        if name == 'abs':
            return SQL('ABS(%s)', self.sql(node.args[0]))
        if name == 'len':
            return SQL('LENGTH(%s)', self.sql(node.args[0]))
        if name == 'round':
            return SQL('ROUND(%s, %s)', self.sql(node.args[0]), self.sql(node.args[1])) if len(node.args) == 2 else SQL('ROUND(%s)', self.sql(node.args[0]))
        if name in {'max', 'min'}:
            return SQL('%s(%s)', SQL('GREATEST' if name == 'max' else 'LEAST'), SQL(', ').join(self.sql(arg) for arg in node.args))
        if name == 'any' and len(node.args) == 1 and isinstance(node.args[0], ast.GeneratorExp):
            return self._any_generator(node.args[0])
        if name == 'timedelta':
            return self._timedelta(node)
        raise _UnsupportedNode(f"Unsupported builtin {name!r}")

    def _timedelta(self, node):
        if node.args:
            raise _UnsupportedNode("Only keyword timedelta() is supported")
        supported = {
            'days': '1 day',
            'seconds': '1 second',
            'microseconds': '1 microsecond',
            'milliseconds': '1 millisecond',
            'minutes': '1 minute',
            'hours': '1 hour',
            'weeks': '1 week',
        }
        parts = []
        for kw in node.keywords:
            if kw.arg not in supported:
                raise _UnsupportedNode(f"Unsupported timedelta unit {kw.arg!r}")
            parts.append(_S()("(%s * INTERVAL %s)", self.sql(kw.value), supported[kw.arg]))
        return _S()('(%s)', _S()(' + ').join(parts)) if parts else _S()("INTERVAL '0 second'")

    def _string_method(self, base, method, args):
        SQL = _S()
        if method in self._STRING_METHODS:
            return SQL(self._STRING_METHODS[method], self.sql(base))
        if method == 'replace' and len(args) == 2:
            return SQL('REPLACE(%s, %s, %s)', self.sql(base), self.sql(args[0]), self.sql(args[1]))
        raise _UnsupportedNode(f"Unsupported string method {method!r}")

    def _inline_record_method(self, method_name, args, keywords):
        if self.ctx.depth >= 4:
            raise _UnsupportedNode(f"Method expansion depth exceeded: {method_name!r}")
        method = getattr(type(self.ctx.model), method_name, None)
        if method is None:
            raise _UnsupportedNode(f"Unknown method {method_name!r}")
        fd = _source_funcdef(method)
        ret = _return_expression(fd.body)
        if ret is None:
            raise _UnsupportedNode(f"Method {method_name!r} is not an expression helper")
        bindings = dict(self.ctx.bindings)
        bindings.update(_call_bindings(fd, args, keywords, self.ctx.record_var))
        return _Compiler(dataclasses.replace(self.ctx, record_var='self', bindings=bindings, depth=self.ctx.depth + 1)).sql(ret)

    def _inline_model_method(self, base, method_name, args, keywords):
        if self.ctx.depth >= 4:
            raise _UnsupportedNode(f"Method expansion depth exceeded: {method_name!r}")
        receiver = self.ctx.model if isinstance(base, ast.Name) and base.id == 'self' else _eval_env(self.ctx.model, base)
        method = getattr(type(receiver), method_name, None)
        if method is None or not getattr(method, '_api_model', False):
            raise _UnsupportedNode(f"Unsupported model helper {method_name!r}")
        try:
            value = method(receiver, *[self._py_const(arg) for arg in args], **{kw.arg: self._py_const(kw.value) for kw in keywords if kw.arg})
        except Exception:
            value = None
        if value is not None and not hasattr(value, '_name'):
            if isinstance(value, (list, tuple, set)):
                return _S()('(%s)', _S()(', ').join(_S()('%s', item) for item in value))
            return _constant_sql(value)
        fd = _source_funcdef(method)
        ret = _return_expression(fd.body)
        if ret is None:
            raise _UnsupportedNode(f"Model helper {method_name!r} is not an expression helper")
        bindings = dict(self.ctx.bindings)
        bindings.update(_call_bindings(fd, args, keywords, self.ctx.record_var))
        return _Compiler(dataclasses.replace(self.ctx, bindings=bindings, depth=self.ctx.depth + 1)).sql(ret)

    def _py_const(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return [self._py_const(elt) for elt in node.elts]
        raise _UnsupportedNode(f"Not a Python constant: {ast.unparse(node)!r}")

    def _any_generator(self, gen):
        from odoo.orm.domains import Domain
        if len(gen.generators) != 1:
            raise _UnsupportedNode("Only single-generator any() is supported")
        comp = gen.generators[0]
        if not isinstance(comp.target, ast.Name):
            raise _UnsupportedNode("Generator target must be a name")
        chain, base = _unroll(comp.iter)
        if not (isinstance(base, ast.Name) and base.id == self.ctx.record_var and chain):
            raise _UnsupportedNode("any() must iterate over a record relation")
        domain_model = self.ctx.model
        for fname in chain:
            field = domain_model._fields.get(fname)
            if not field or not field.comodel_name:
                raise _UnsupportedNode(f"Cannot iterate over {fname!r}")
            domain_model = domain_model.env[field.comodel_name]
        domain = _domain_from_ast(gen.elt, comp.target.id, domain_model)
        for fname in reversed(chain):
            domain = Domain(fname, 'any', domain)
        return domain.optimize_full(self.ctx.model)._to_sql(self.ctx.table)

    def _coerce_bool(self, node, sql):
        SQL = _S()
        field_type = self._field_type(node)
        if field_type in {'char', 'text', 'html', 'selection'}:
            return SQL('(%s IS NOT NULL AND %s != %s)', sql, sql, '')
        if field_type in {'integer', 'float', 'monetary'}:
            return SQL('(%s IS NOT NULL AND %s != 0)', sql, sql)
        if field_type == 'boolean':
            return SQL('(%s IS TRUE)', sql)
        return SQL('(%s IS NOT NULL)', sql)

    def _field_type(self, node):
        chain, base = _unroll(node)
        if isinstance(base, ast.Name) and base.id == self.ctx.record_var:
            return _field_type_for_chain(self.ctx.model, chain)
        return 'unknown'


def _domain_from_ast(node: ast.expr, record_var: str, model):
    from odoo.orm.domains import Domain

    def field_name(expr):
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id == record_var:
            return expr.attr
        return None

    if isinstance(node, ast.BoolOp):
        parts = [_domain_from_ast(value, record_var, model) for value in node.values]
        domain = parts[0]
        for part in parts[1:]:
            domain = domain & part if isinstance(node.op, ast.And) else domain | part
        return domain
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return ~_domain_from_ast(node.operand, record_var, model)
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and (fname := field_name(node.left)):
        op = {ast.Eq: '=', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>='}.get(type(node.ops[0]))
        if op:
            return Domain(fname, op, _const(node.comparators[0]))
        if isinstance(node.ops[0], ast.In):
            return Domain(fname, 'in', _const_seq(node.comparators[0]))
        if isinstance(node.ops[0], ast.NotIn):
            return Domain(fname, 'not in', _const_seq(node.comparators[0]))
    if fname := field_name(node):
        field = model._fields.get(fname)
        if field and field.type in {'char', 'text', 'html', 'selection'}:
            return Domain(fname, 'not in', [False, '', None])
        return Domain(fname, '!=', False)
    raise _UnsupportedNode(f"Cannot lower any() expression: {ast.unparse(node)!r}")


# ---------------------------------------------------------------------------
# Compute-shape extraction
# ---------------------------------------------------------------------------

def _return_expression(stmts):
    if not stmts:
        return None
    stmt = stmts[0]
    if isinstance(stmt, ast.Return) and stmt.value:
        return stmt.value
    if isinstance(stmt, ast.If):
        body = _return_expression(stmt.body)
        orelse = _return_expression(stmt.orelse or stmts[1:])
        if body is not None and orelse is not None:
            return ast.IfExp(test=stmt.test, body=body, orelse=orelse)
    return None


def _call_bindings(fd, args, keywords, outer_record_var):
    params = [arg.arg for arg in fd.args.args if arg.arg != 'self']
    defaults = fd.args.defaults
    default_offset = len(params) - len(defaults)
    bindings = {}
    for index, arg in enumerate(args):
        if index < len(params):
            bindings[params[index]] = arg
    for kw in keywords:
        if kw.arg:
            bindings[kw.arg] = kw.value
    for index, param in enumerate(params):
        if param not in bindings and index >= default_offset:
            bindings[param] = defaults[index - default_offset]
    for key, value in list(bindings.items()):
        if isinstance(value, ast.expr):
            bindings[key] = _rewrite_name(value, outer_record_var, 'self')
    return bindings


class _LoopFinder(ast.NodeVisitor):
    def __init__(self):
        self.record_var = None
        self.body = None
        self.extra_bindings = {}

    def find(self, stmts):
        for stmt in stmts:
            self.visit(stmt)
            if self.record_var:
                return True
        return False

    def visit_For(self, node):
        if isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Name) and node.iter.id == 'self' and not node.orelse:
            self.record_var = node.target.id
            self.body = node.body
            return
        if (
            isinstance(node.target, ast.Tuple)
            and len(node.target.elts) == 2
            and all(isinstance(elt, ast.Name) for elt in node.target.elts)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == 'zip'
            and len(node.iter.args) == 2
            and isinstance(node.iter.args[0], ast.Name)
            and node.iter.args[0].id == 'self'
            and _is_env_expr(node.iter.args[1])
        ):
            self.record_var = node.target.elts[0].id
            self.body = node.body
            self.extra_bindings[node.target.elts[1].id] = _RecordVariant(node.iter.args[1])


class _LocalCollector:
    def __init__(self, record_var, model):
        self.record_var = record_var
        self.model = model
        self.bindings = {}

    def collect(self, stmts):
        for stmt in stmts:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                self.bindings[stmt.targets[0].id] = self._binding(stmt.value)

    def _binding(self, value):
        if _is_env_expr(value):
            return _EnvConst(value)
        return value


class _AssignmentExtractor:
    def __init__(self, record_var, field_name):
        self.record_var = record_var
        self.field_name = field_name

    def extract(self, stmts):
        if stmts and (fallback := self._fallback(stmts[-1])) is not None:
            base = self._stmts(stmts[:-1], [])
            if base is not None:
                return ast.BoolOp(op=ast.Or(), values=[base, fallback])
        return self._stmts(stmts, [])

    def _is_target(self, node):
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == self.record_var
            and node.attr == self.field_name
        )

    def _fallback(self, stmt):
        if (
            isinstance(stmt, ast.If)
            and len(stmt.body) == 1
            and not stmt.orelse
            and isinstance(stmt.test, ast.UnaryOp)
            and isinstance(stmt.test.op, ast.Not)
            and self._is_target(stmt.test.operand)
            and isinstance(stmt.body[0], ast.Assign)
            and len(stmt.body[0].targets) == 1
            and self._is_target(stmt.body[0].targets[0])
        ):
            return stmt.body[0].value
        return None

    def _stmts(self, stmts, remaining):
        for index, stmt in enumerate(stmts):
            value = self._stmt(stmt, list(stmts[index + 1:]) + remaining)
            if value is not None:
                return value
        return None

    def _stmt(self, stmt, remaining):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if self._is_target(target):
                return stmt.value
            if isinstance(target, (ast.Tuple, ast.List)):
                for index, elt in enumerate(target.elts):
                    if self._is_target(elt):
                        return ast.Subscript(value=stmt.value, slice=ast.Constant(index), ctx=ast.Load())
        if isinstance(stmt, ast.If):
            return self._if(stmt, remaining)
        return None

    def _if(self, node, remaining):
        is_guard = node.body and isinstance(node.body[-1], ast.Continue) and not node.orelse
        body_value = self._stmts(node.body[:-1] if is_guard else node.body, [])
        if is_guard:
            else_value = self._stmts(remaining, [])
        elif node.orelse and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            else_value = self._if(node.orelse[0], remaining)
        else:
            else_value = self._stmts(node.orelse, []) if node.orelse else self._stmts(remaining, [])
        if body_value is None and else_value is None:
            return None
        if body_value is None:
            return else_value
        if else_value is None:
            return ast.IfExp(test=node.test, body=body_value, orelse=ast.Constant(None))
        return ast.IfExp(test=node.test, body=body_value, orelse=else_value)


class _SelfFieldReference(ast.NodeVisitor):
    def __init__(self, record_var, field_name):
        self.record_var = record_var
        self.field_name = field_name
        self.found = False

    def visit_Attribute(self, node):
        if self.found:
            return
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == self.record_var
            and node.attr == self.field_name
        ):
            self.found = True
            return
        self.generic_visit(node)


def _is_assignment_target(node, record_var, field_name):
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == record_var
        and node.attr == field_name
    )


def _straightline_assignment_count(stmts, record_var, field_name):
    count = 0
    for stmt in stmts:
        if not isinstance(stmt, ast.Assign):
            continue
        for target in stmt.targets:
            if _is_assignment_target(target, record_var, field_name):
                count += 1
            elif isinstance(target, (ast.Tuple, ast.List)):
                count += sum(_is_assignment_target(elt, record_var, field_name) for elt in target.elts)
    return count


def _pre_loop_stmts(fd, record_var):
    stmts = []
    for stmt in fd.body:
        if (
            isinstance(stmt, ast.For)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == record_var
            and isinstance(stmt.iter, ast.Name)
            and stmt.iter.id == 'self'
        ):
            return stmts
        stmts.append(stmt)
    return []


def _recordset_assignment(fd, field_name):
    for stmt in fd.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self' and target.attr == field_name:
            return _Spec('self', {}, stmt.value)
    return None


# ---------------------------------------------------------------------------
# SQL projection computes
# ---------------------------------------------------------------------------

def _table_field_name(node):
    chain, base = _unroll(node)
    if isinstance(base, ast.Name) and chain == ['table']:
        return 'id'
    if isinstance(base, ast.Name) and len(chain) == 2 and chain[0] == 'table':
        return chain[1]
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == 'table'
        and isinstance(node.value.value, ast.Name)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    ):
        return node.slice.value
    return None


def _field_source(model, field_name):
    if field_name == 'id':
        return _FieldSQL('id')
    field = model._fields.get(field_name)
    if field and (field.store or field.compute_sql):
        return _FieldSQL(field_name)
    method_name = f'_compute_sql_{field_name}'
    if hasattr(type(model), method_name):
        return _MethodSQL(method_name)
    return None


def _select_call(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dict' and len(node.args) == 1:
        node = node.args[0]
    if isinstance(node, ast.DictComp) and len(node.generators) == 1:
        node = node.generators[0].iter
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'execute_query'
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Call)
        and isinstance(node.args[0].func, ast.Attribute)
        and node.args[0].func.attr == 'select'
    ):
        return node.args[0]
    return None


def _starred_sources(arg, model):
    gen = arg.value
    if not (
        isinstance(gen, ast.GeneratorExp)
        and len(gen.generators) == 1
        and isinstance(gen.generators[0].target, ast.Name)
        and isinstance(gen.generators[0].iter, (ast.Tuple, ast.List))
        and isinstance(gen.elt, ast.Subscript)
        and isinstance(gen.elt.slice, ast.Name)
        and gen.elt.slice.id == gen.generators[0].target.id
    ):
        return None
    chain, base = _unroll(gen.elt.value)
    if not (isinstance(base, ast.Name) and chain == ['table']):
        return None
    sources = []
    for elt in gen.generators[0].iter.elts:
        source = _field_source(model, _const(elt))
        if source is None:
            return None
        sources.append(source)
    return sources


def _select_sources(select_call, local_sql, model):
    sources = []
    for arg in select_call.args:
        if isinstance(arg, ast.Starred):
            starred = _starred_sources(arg, model)
            if starred is None:
                return None
            sources.extend(starred)
        elif isinstance(arg, ast.Name) and arg.id in local_sql:
            sources.append(local_sql[arg.id])
        elif fname := _table_field_name(arg):
            source = _field_source(model, fname)
            if source is None:
                return None
            sources.append(source)
        else:
            return None
    return sources


class _ProjectionLookupRewriter(ast.NodeTransformer):
    def __init__(self, record_var, projection_vars):
        self.record_var = record_var
        self.projection_vars = projection_vars

    def visit_Call(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == 'get'
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in self.projection_vars
            and node.args
            and _is_record_id(node.args[0], self.record_var)
            and len(self.projection_vars[node.func.value.id]) == 1
        ):
            return ast.copy_location(ast.Name(id=self.projection_vars[node.func.value.id][0], ctx=ast.Load()), node)
        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == 'get'
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id in self.projection_vars
            and node.value.args
            and _is_record_id(node.value.args[0], self.record_var)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, int)
            and node.slice.value < len(self.projection_vars[node.value.func.value.id])
        ):
            return ast.copy_location(ast.Name(id=self.projection_vars[node.value.func.value.id][node.slice.value], ctx=ast.Load()), node)
        if (
            isinstance(node.value, ast.Name)
            and node.value.id in self.projection_vars
            and _is_record_id(node.slice, self.record_var)
            and len(self.projection_vars[node.value.id]) == 1
        ):
            return ast.copy_location(ast.Name(id=self.projection_vars[node.value.id][0], ctx=ast.Load()), node)
        return node


def _projection_local_bindings(stmts, projection_vars):
    bindings = {}
    for stmt in stmts:
        if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], (ast.Tuple, ast.List))):
            continue
        value = stmt.value
        projection_var = None
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == 'get' and isinstance(value.func.value, ast.Name):
            projection_var = value.func.value.id
        if projection_var not in projection_vars:
            continue
        for index, target in enumerate(stmt.targets[0].elts):
            if isinstance(target, ast.Name) and index < len(projection_vars[projection_var]):
                bindings[target.id] = ast.Subscript(value=value, slice=ast.Constant(index), ctx=ast.Load())
    return bindings


def _query_projection_spec(fd, field_name, model):
    loop = _LoopFinder()
    if not loop.find(fd.body):
        return None

    local_sql = {}
    for stmt in fd.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and isinstance(stmt.value.func.value, ast.Name)
            and stmt.value.func.value.id == 'self'
            and stmt.value.args
        ):
            chain, base = _unroll(stmt.value.args[0])
            if isinstance(base, ast.Name) and chain == ['table']:
                local_sql[stmt.targets[0].id] = _MethodSQL(stmt.value.func.attr)

    projections = {}
    bindings = {}
    for stmt in fd.body:
        if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
            continue
        select = _select_call(stmt.value)
        if select is None:
            continue
        sources = _select_sources(select, local_sql, model)
        if not sources or len(sources) < 2:
            continue
        names = []
        for index, source in enumerate(sources[1:]):
            name = stmt.targets[0].id if len(sources) == 2 else f'__{stmt.targets[0].id}_{index}'
            bindings[name] = source
            names.append(name)
        projections[stmt.targets[0].id] = names
    if not projections:
        return None
    target = _AssignmentExtractor(loop.record_var, field_name).extract(loop.body)
    if target is None:
        return None
    local_bindings = _projection_local_bindings(loop.body, projections)
    if isinstance(target, ast.Name) and target.id in local_bindings:
        target = local_bindings[target.id]
    target = _ProjectionLookupRewriter(loop.record_var, projections).visit(target)
    return _Spec(loop.record_var, bindings, ast.fix_missing_locations(target))


def _execute_query_loop_spec(fd, field_name, model):
    for stmt in fd.body:
        if not (
            isinstance(stmt, ast.For)
            and isinstance(stmt.target, (ast.Tuple, ast.List))
            and all(isinstance(elt, ast.Name) for elt in stmt.target.elts)
            and (select := _select_call(stmt.iter))
        ):
            continue
        sources = _select_sources(select, {}, model)
        if not sources or len(sources) != len(stmt.target.elts):
            continue
        id_var = stmt.target.elts[0].id
        record_vars = set()
        for body_stmt in stmt.body:
            if (
                isinstance(body_stmt, ast.Assign)
                and len(body_stmt.targets) == 1
                and isinstance(body_stmt.targets[0], ast.Name)
                and isinstance(body_stmt.value, ast.Call)
                and isinstance(body_stmt.value.func, ast.Attribute)
                and body_stmt.value.func.attr == 'browse'
                and isinstance(body_stmt.value.func.value, ast.Name)
                and body_stmt.value.func.value.id == 'self'
                and len(body_stmt.value.args) == 1
                and isinstance(body_stmt.value.args[0], ast.Name)
                and body_stmt.value.args[0].id == id_var
            ):
                record_vars.add(body_stmt.targets[0].id)
        value_sources = {target.id: source for target, source in zip(stmt.target.elts[1:], sources[1:])}
        for body_stmt in stmt.body:
            if (
                isinstance(body_stmt, ast.Assign)
                and len(body_stmt.targets) == 1
                and isinstance(body_stmt.targets[0], ast.Attribute)
                and isinstance(body_stmt.targets[0].value, ast.Name)
                and body_stmt.targets[0].value.id in record_vars
                and body_stmt.targets[0].attr == field_name
                and isinstance(body_stmt.value, ast.Name)
                and body_stmt.value.id in value_sources
            ):
                name = f'__query_loop_{field_name}'
                return _Spec(body_stmt.targets[0].value.id, {name: value_sources[body_stmt.value.id]}, ast.Name(id=name, ctx=ast.Load()))
    return None


# ---------------------------------------------------------------------------
# Semantic adapters for computes that do not expose a formula in Python.
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Spec construction, validation, public API
# ---------------------------------------------------------------------------

def _compute_sql_spec(compute_name: str | Callable, field_name: str, model):
    if callable(compute_name):
        if adapter := _semantic_adapter(None, field_name, model):
            return adapter
        raw = compute_name
        label = getattr(raw, '__name__', repr(raw))
    else:
        raw = getattr(type(model), compute_name, None)
        label = compute_name
    if raw is None:
        raise _UnsupportedNode(f"Compute method {label!r} not found on {model._name!r}")
    fd = _source_funcdef(raw)

    if adapter := _semantic_adapter(fd, field_name, model):
        return adapter
    if spec := _query_projection_spec(fd, field_name, model):
        _validate_spec(spec, field_name, model)
        return spec
    if spec := _execute_query_loop_spec(fd, field_name, model):
        _validate_spec(spec, field_name, model)
        return spec
    if spec := _recordset_assignment(fd, field_name):
        spec = dataclasses.replace(spec, bindings={'__model__': model})
        _validate_spec(spec, field_name, model)
        return spec

    loop = _LoopFinder()
    if not loop.find(fd.body):
        raise _UnsupportedNode(f"No 'for record in self' loop in {label!r}")
    collector = _LocalCollector(loop.record_var, model)
    collector.bindings.update(loop.extra_bindings)
    collector.collect(_pre_loop_stmts(fd, loop.record_var))
    collector.collect(loop.body)
    if _straightline_assignment_count(loop.body, loop.record_var, field_name) > 1:
        raise _UnsupportedNode(f"Multiple straight-line assignments to {field_name!r}")
    target = _AssignmentExtractor(loop.record_var, field_name).extract(loop.body)
    if target is None:
        raise _UnsupportedNode(f"No assignment to {field_name!r} in {label!r}")
    self_ref = _SelfFieldReference(loop.record_var, field_name)
    self_ref.visit(target)
    if self_ref.found:
        raise _UnsupportedNode(f"Expression for {field_name!r} reads itself")
    spec = _Spec(loop.record_var, {**collector.bindings, '__model__': model}, target)
    _validate_spec(spec, field_name, model)
    return spec


def _validate_spec(spec, field_name, model):
    # Build-time validation is intentionally shallow.  The real SQL objects need
    # an ORM table, but these checks catch unsupported references before the
    # field is marked searchable/orderable.
    for node in ast.walk(spec.target):
        if isinstance(node, ast.Attribute):
            chain, base = _unroll(node)
            if isinstance(base, ast.Name) and base.id == spec.record_var and chain:
                if chain[0] in {'_origin'}:
                    chain = chain[1:]
                if not chain:
                    continue
                current = model
                for index, fname in enumerate(chain):
                    if fname == 'id':
                        break
                    field = current._fields.get(fname)
                    if field is None:
                        # The AST walker also sees method-call attributes such
                        # as ``record.sudo`` and recordset implementation
                        # attributes.  They are checked by the lowerer when the
                        # complete expression is compiled.
                        break
                    if index == 0 and fname == field_name:
                        raise _UnsupportedNode(f"Expression for {field_name!r} reads itself")
                    if index == len(chain) - 1 and not field.store and not field.compute_sql and not field.related:
                        raise _UnsupportedNode(f"Non-stored field {fname!r} has no SQL")
                    if index != len(chain) - 1:
                        if not field.comodel_name:
                            raise _UnsupportedNode(f"Cannot traverse non-relational field {fname!r}")
                        current = current.env[field.comodel_name]


def _normalize_sql(sql):
    return re.sub(r'\s+', ' ', getattr(sql, '_sql_tuple', ('',))[0]).strip()


def _efficiency_warnings(sql):
    code = _normalize_sql(sql)
    warnings = []
    if len(code) > 12000:
        warnings.append(f"large generated SQL expression ({len(code)} characters)")
    exists_count = code.upper().count('EXISTS')
    fragments = _EXPENSIVE_RE.findall(code)
    if exists_count > 1:
        warnings.append("multiple EXISTS subqueries")
    if fragments and len(set(fragments)) < len(fragments):
        warnings.append("duplicated EXISTS subqueries")
    if re.search(r'EXISTS\s*\([^)]*\bEXISTS\s*\(', code, re.IGNORECASE | re.DOTALL):
        warnings.append("nested EXISTS subqueries")
    return warnings


def _make_auto_compute_sql(compute_name: str, field_name: str, model=None):
    """Return a lazy ``(model, table) -> SQL`` callable, or ``None``."""
    cache = {}
    warned = set()

    def warn_if_needed(model_, sql):
        reasons = _efficiency_warnings(sql)
        key = (type(model_), field_name)
        if reasons and key not in warned:
            warned.add(key)
            _logger.warning(
                "Auto compute_sql for %s.%s generated potentially inefficient SQL: %s",
                model_._name, field_name, "; ".join(reasons),
            )

    def parse(model_):
        cls = type(model_)
        spec = _compute_sql_spec(compute_name, field_name, model_)
        if callable(spec):
            def compute(model__, table):
                sql = spec(model__, table)
                warn_if_needed(model__, sql)
                return sql
            cache[cls] = compute
            return compute

        def compute(model__, table):
            ctx = _Ctx(spec.record_var, model__, table, dict(spec.bindings), model__._fields[field_name].type)
            try:
                sql = _Compiler(ctx).value_sql(spec.target)
            except _UnsupportedNode as exc:
                raise ValueError(f"compute_sql derivation failed for {field_name!r}: {exc}") from exc
            warn_if_needed(model__, sql)
            return sql

        cache[cls] = compute
        return compute

    if model is not None:
        try:
            parse(model)
        except _UnsupportedNode as exc:
            _logger.debug("auto compute_sql skipped for %s.%s: %s", model._name, field_name, exc)
            return None

    def _auto_compute_sql(model_, table):
        fn = cache.get(type(model_))
        if fn is None:
            try:
                fn = parse(model_)
            except _UnsupportedNode as exc:
                raise ValueError(f"compute_sql derivation failed for {field_name!r}: {exc}") from exc
        return fn(model_, table)

    _auto_compute_sql.__name__ = f'_auto_compute_sql__{field_name}'
    return _auto_compute_sql
