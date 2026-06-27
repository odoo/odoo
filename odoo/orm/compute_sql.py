# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Auto-derive ``compute_sql`` for non-stored computed fields by transpiling
their Python compute method to SQL at field-setup time.

Supported patterns:  field reads, chained Many2one access, arithmetic,
comparisons, boolean ops, ternary / if-elif-else chains, continue-guards,
local variable aliases, One2many virtual-recordset operations (sorted /
filtered / [:1] / bool / .field), ``any()`` generators via Domain, inlining of
``@api.model`` and simple record methods.  Any unsupported pattern raises
``_UnsupportedNode`` and the caller silently leaves ``compute_sql`` unset.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import logging
import textwrap
from typing import Any, Callable

_logger = logging.getLogger(__name__)


class _UnsupportedNode(Exception):
    """Raised for AST patterns that cannot be transpiled to SQL."""


# ── Lazy SQL import (avoid circular imports at module load) ─────────────────

def _S():
    from odoo.tools import SQL
    return SQL


# ── AST helpers ─────────────────────────────────────────────────────────────

def _unroll(node: ast.expr) -> tuple[list[str], ast.expr]:
    """Unroll ``a.b.c`` → (['b','c'], Name('a'))."""
    chain: list[str] = []
    while isinstance(node, ast.Attribute):
        chain.append(node.attr)
        node = node.value
    chain.reverse()
    return chain, node


def _const(node: ast.expr) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    raise _UnsupportedNode(f"Expected constant, got {ast.unparse(node)!r}")


def _seq(node: ast.expr) -> list[Any]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_const(e) for e in node.elts]
    raise _UnsupportedNode(f"Expected sequence, got {ast.unparse(node)!r}")


def _field_type_for_chain(model, chain: list[str]) -> str:
    for i, fname in enumerate(chain):
        field = model._fields.get(fname)
        if field is None:
            return 'unknown'
        if i == len(chain) - 1:
            return field.type
        if not field.comodel_name:
            return 'unknown'
        model = model.env[field.comodel_name]
    return 'unknown'


_SENTINEL = object()


# ── Virtual-recordset spec (immutable, cached) and runtime object ───────────

@dataclasses.dataclass(frozen=True)
class _VRSSpec:
    field_name: str
    order_by: tuple = ()            # ((col, reverse), ...)
    filter_lambdas: tuple = ()      # ((var, ast.expr), ...)
    is_limited: bool = False


@dataclasses.dataclass
class _VRS:
    cotable: str
    fk_col: str
    parent_id: Any          # SQL expr for parent.id
    order_by: list
    filter_sqls: list
    is_limited: bool = False

    def _q(self, select, alias='__vrs'):
        SQL = _S()
        al = SQL.identifier(alias)
        conds = [SQL('%s = %s', SQL.identifier(alias, self.fk_col), self.parent_id), *self.filter_sqls]
        q = SQL('SELECT %s FROM %s AS %s WHERE %s',
                select, SQL.identifier(self.cotable), al, SQL(' AND ').join(conds))
        if self.order_by:
            q = SQL('%s ORDER BY %s', q, SQL(', ').join(
                SQL('%s %s', SQL.identifier(alias, c), SQL('DESC' if r else 'ASC'))
                for c, r in self.order_by))
        return q

    def exists_sql(self):     return _S()('EXISTS (%s)', self._q(_S()('1')))
    def not_exists_sql(self): return _S()('NOT EXISTS (%s)', self._q(_S()('1')))
    def field_sql(self, fname): return _S()('(%s LIMIT 1)', self._q(_S().identifier('__vrs', fname)))


def _build_vrs(spec: _VRSSpec, model, table) -> _VRS:
    from odoo.orm.query import Query
    SQL = _S()
    field = model._fields[spec.field_name]
    comodel = model.env[field.comodel_name]
    filter_sqls = []
    for lvar, body in spec.filter_lambdas:
        sub = Query(comodel, alias='__vrs').table
        ctx = _Ctx(lvar, comodel, sub, {})
        filter_sqls.append(_Transpiler(ctx).to_sql(body))
    return _VRS(comodel._table, field.inverse_name,
                SQL.identifier(table._alias, 'id'),
                list(spec.order_by), filter_sqls, spec.is_limited)


# ── Transpilation context ────────────────────────────────────────────────────

@dataclasses.dataclass
class _Ctx:
    record_var: str
    model: Any
    table: Any
    bindings: dict
    target_type: str | None = None
    depth: int = 0
    _MAX_DEPTH: int = dataclasses.field(default=4, init=False, repr=False)


# ── Main transpiler ──────────────────────────────────────────────────────────

class _Transpiler:
    def __init__(self, ctx: _Ctx):
        self.ctx = ctx
        self._expanding_names = set()
        self._value_depth = 0

    def to_sql(self, node: ast.expr) -> Any:
        m = getattr(self, f'visit_{type(node).__name__}', None)
        if m is None:
            raise _UnsupportedNode(f"Unsupported node {type(node).__name__}: {ast.unparse(node)!r}")
        return m(node)

    def _value_sql(self, node: ast.expr) -> Any:
        self._value_depth += 1
        try:
            return self.to_sql(node)
        finally:
            self._value_depth -= 1

    # ── literals ──
    def visit_Constant(self, n):
        SQL = _S()
        if n.value is None:  return SQL('NULL')
        if isinstance(n.value, bool):
            if n.value is False and self._value_depth and self.ctx.target_type != 'boolean':
                return SQL('NULL')
            return SQL('TRUE') if n.value else SQL('FALSE')
        return SQL('%s', n.value)

    def visit_Tuple(self, n): return [_const(e) for e in n.elts]
    def visit_List(self, n):  return [_const(e) for e in n.elts]

    # ── names ──
    def visit_Name(self, n):
        SQL = _S()
        if n.id == 'True':  return SQL('TRUE')
        if n.id == 'False': return SQL('FALSE')
        if n.id == 'None':  return SQL('NULL')
        b = self.ctx.bindings.get(n.id)
        if b is None: raise _UnsupportedNode(f"Unresolved name {n.id!r}")
        if isinstance(b, _VRSSpec): return _build_vrs(b, self.ctx.model, self.ctx.table).exists_sql()
        if isinstance(b, _VRS):    return b.exists_sql()
        if isinstance(b, ast.expr):
            if n.id in self._expanding_names:
                raise _UnsupportedNode(f"Recursive binding for {n.id!r}")
            self._expanding_names.add(n.id)
            try:
                return self.to_sql(b)
            finally:
                self._expanding_names.remove(n.id)
        raise _UnsupportedNode(f"Unknown binding type for {n.id!r}")

    # ── attribute / field access ──
    def visit_Attribute(self, n):
        chain, base = _unroll(n)
        if isinstance(base, ast.Name) and base.id == self.ctx.record_var:
            sql = self.ctx.table
            for fname in chain: sql = sql[fname]
            return sql
        if isinstance(base, ast.Name) and base.id in self.ctx.bindings:
            b = self.ctx.bindings[base.id]
            if isinstance(b, (_VRSSpec, _VRS)):
                if len(chain) != 1: raise _UnsupportedNode(f"Deep VRS access: {ast.unparse(n)!r}")
                vrs = b if isinstance(b, _VRS) else _build_vrs(b, self.ctx.model, self.ctx.table)
                return vrs.field_sql(chain[0])
        raise _UnsupportedNode(f"Unsupported attribute: {ast.unparse(n)!r}")

    # ── arithmetic ──
    _OPS = {ast.Add:'+', ast.Sub:'-', ast.Mult:'*', ast.Div:'/', ast.FloorDiv:'/', ast.Mod:'%'}

    def visit_BinOp(self, n):
        op = self._OPS.get(type(n.op))
        if op is None: raise _UnsupportedNode(f"Unsupported op: {type(n.op).__name__}")
        return _S()(f'(%s {op} %s)', self.to_sql(n.left), self.to_sql(n.right))

    # ── comparisons ──
    def visit_Compare(self, n):
        SQL = _S()
        if len(n.ops) != 1: raise _UnsupportedNode("Chained comparisons not supported")
        op, rn = n.ops[0], n.comparators[0]
        left = self.to_sql(n.left)
        if isinstance(op, (ast.In, ast.NotIn)):
            neg = isinstance(op, ast.NotIn)
            op_in, op_not_in = ('IN', 'NOT IN') if not neg else ('NOT IN', 'IN')
            # Try to evaluate the RHS as SQL first (handles method-call results).
            try:
                rhs = self.to_sql(rn)
            except _UnsupportedNode:
                rhs = None
            if isinstance(rhs, list):  # visit_List / visit_Tuple
                vals = rhs
            elif rhs is not None:  # SQL object with parens, e.g. from _eval_api_model
                return SQL('(%s %s %s)', left, SQL(op_in), rhs)
            else:
                vals = self._seq(rn)
            if not vals:
                return SQL('FALSE') if not neg else SQL('TRUE')
            ph = SQL(', ').join(SQL('%s', v) for v in vals)
            return SQL('(%s %s (%s))', left, SQL(op_in), ph)
        right = self.to_sql(rn)
        m = {ast.Eq:'=', ast.NotEq:'!=', ast.Lt:'<', ast.LtE:'<=', ast.Gt:'>', ast.GtE:'>='}
        s = m.get(type(op))
        if s is None: raise _UnsupportedNode(f"Unsupported cmp: {type(op).__name__}")
        if isinstance(rn, ast.Constant) and rn.value is None:
            return SQL('(%s IS NULL)', left) if s == '=' else SQL('(%s IS NOT NULL)', left)
        return SQL(f'(%s {s} %s)', left, right)

    def _seq(self, n):
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)): return [_const(e) for e in n.elts]
        return [_const(n)]

    # ── boolean ops (with constant folding) ──
    def _pyval(self, n):
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.Name):
            b = self.ctx.bindings.get(n.id)
            if isinstance(b, ast.Constant): return b.value
        return _SENTINEL

    def visit_BoolOp(self, n):
        """Value-mode BoolOp: returns raw SQL when folded to a single part."""
        return self._boolop(n, bool_mode=False)

    def _boolop(self, n, bool_mode: bool):
        """Core BoolOp logic.  bool_mode=True coerces single-part results to bool."""
        SQL = _S()
        is_and = isinstance(n.op, ast.And)
        parts = []
        for v in n.values:
            pv = self._pyval(v)
            if pv is not _SENTINEL:
                if is_and and not pv: return SQL('FALSE')
                if not is_and and pv: return SQL('TRUE')
            else:
                parts.append(v)
        if not parts: return SQL('TRUE') if is_and else SQL('FALSE')
        if len(parts) == 1:
            return self._bool(parts[0]) if bool_mode else self.to_sql(parts[0])
        sep = ' AND ' if is_and else ' OR '
        return SQL('(%s)', SQL(sep).join(self._bool(v) for v in parts))

    def visit_UnaryOp(self, n):
        SQL = _S()
        if isinstance(n.op, ast.Not):
            if isinstance(n.operand, ast.Name) and n.operand.id in self.ctx.bindings:
                b = self.ctx.bindings[n.operand.id]
                if isinstance(b, (_VRSSpec, _VRS)):
                    vrs = b if isinstance(b, _VRS) else _build_vrs(b, self.ctx.model, self.ctx.table)
                    return vrs.not_exists_sql()
            return SQL('(NOT %s)', self._bool(n.operand))
        if isinstance(n.op, ast.USub): return SQL('(-%s)', self.to_sql(n.operand))
        if isinstance(n.op, ast.UAdd): return self.to_sql(n.operand)
        raise _UnsupportedNode(f"Unsupported unary: {type(n.op).__name__}")

    def _bool(self, node: ast.expr) -> Any:
        """Transpile a node ensuring the result is a boolean SQL expression."""
        value_depth = self._value_depth
        self._value_depth = 0
        try:
            if isinstance(node, ast.BoolOp):
                return self._boolop(node, bool_mode=True)
            sql = self.to_sql(node)
            if isinstance(node, (ast.Compare, ast.UnaryOp)): return sql
            return self._coerce_bool(node, sql)
        finally:
            self._value_depth = value_depth

    def _coerce_bool(self, node, sql) -> Any:
        SQL = _S()
        ft = self._field_type(node)
        if ft in ('char', 'text', 'html', 'selection'):
            return SQL('(%s IS NOT NULL AND %s != %s)', sql, sql, SQL('%s', ''))
        if ft in ('integer', 'float', 'monetary'):
            return SQL('(%s IS NOT NULL AND %s != 0)', sql, sql)
        if ft == 'many2one':
            return SQL('(%s IS NOT NULL)', sql)
        return SQL('(%s IS NOT NULL AND %s IS NOT FALSE)', sql, sql)

    def _field_type(self, node) -> str:
        try:
            chain, base = _unroll(node)
            if isinstance(base, ast.Name):
                if base.id == self.ctx.record_var and chain:
                    return _field_type_for_chain(self.ctx.model, chain)
                elif base.id in self.ctx.bindings and chain:
                    b = self.ctx.bindings[base.id]
                    if isinstance(b, _VRSSpec):
                        frel = self.ctx.model._fields.get(b.field_name)
                        if frel:
                            return _field_type_for_chain(self.ctx.model.env[frel.comodel_name], chain)
        except Exception: pass
        return 'unknown'

    # ── ternary ──
    def visit_IfExp(self, n):
        SQL = _S()
        pv = self._pyval(n.test)
        if pv is not _SENTINEL: return self._value_sql(n.body if pv else n.orelse)
        return SQL('CASE WHEN %s THEN %s ELSE %s END', self._bool(n.test), self._value_sql(n.body), self._value_sql(n.orelse))

    def visit_Subscript(self, n):
        raise _UnsupportedNode(f"Subscript in expression context: {ast.unparse(n)!r}")

    # ── calls ──
    def visit_Call(self, n):
        if isinstance(n.func, ast.Name):
            if n.func.id == 'any' and len(n.args) == 1 and isinstance(n.args[0], ast.GeneratorExp):
                return self._any_gen(n.args[0])
            return self._builtin(n)
        if isinstance(n.func, ast.Attribute):
            chain, base = _unroll(n.func)
            if isinstance(base, ast.Name) and base.id == self.ctx.record_var and len(chain) == 1:
                return self._inline_method(chain[0], n.args, n.keywords)
            if len(chain) == 1:
                return self._str_method(base, chain[0], n.args)
        raise _UnsupportedNode(f"Unsupported call: {ast.unparse(n)!r}")

    def _builtin(self, n):
        SQL = _S()
        nm = n.func.id
        if nm in ('str', 'int', 'float'):
            return SQL('(%s::%s)', self.to_sql(n.args[0]), SQL({'str':'text','int':'integer','float':'float8'}[nm]))
        if nm == 'bool':   return self._bool(n.args[0])
        if nm == 'abs':    return SQL('ABS(%s)', self.to_sql(n.args[0]))
        if nm == 'len':    return SQL('LENGTH(%s)', self.to_sql(n.args[0]))
        if nm == 'round':
            a = self.to_sql(n.args[0])
            return SQL('ROUND(%s, %s)', a, self.to_sql(n.args[1])) if len(n.args) == 2 else SQL('ROUND(%s)', a)
        if nm in ('max', 'min'):
            fn = 'GREATEST' if nm == 'max' else 'LEAST'
            return SQL('%s(%s)', SQL(fn), SQL(', ').join(self.to_sql(a) for a in n.args))
        raise _UnsupportedNode(f"Unsupported builtin: {nm!r}")

    def _str_method(self, obj_node, method, args):
        SQL = _S(); obj = self.to_sql(obj_node)
        m = {'upper':'UPPER(%s)', 'lower':'LOWER(%s)', 'strip':'TRIM(%s)', 'lstrip':'LTRIM(%s)', 'rstrip':'RTRIM(%s)'}
        if method in m: return SQL(m[method], obj)
        if method == 'replace' and len(args) == 2:
            return SQL('REPLACE(%s, %s, %s)', obj, self.to_sql(args[0]), self.to_sql(args[1]))
        raise _UnsupportedNode(f"Unsupported string method: {method!r}")

    def _inline_method(self, name, call_args, call_kws):
        if self.ctx.depth >= self.ctx._MAX_DEPTH:
            raise _UnsupportedNode(f"Method expansion depth exceeded: {name!r}")
        method = getattr(type(self.ctx.model), name, None)
        if method is None:
            raise _UnsupportedNode(f"Method {name!r} not found on {self.ctx.model._name!r}")
        if getattr(method, '_api_model', False):
            r = self._eval_api_model(method, call_args, call_kws)
            if r is not None: return r
        try:
            src = textwrap.dedent(inspect.getsource(getattr(method, '__wrapped__', method)))
            tree = ast.parse(src)
        except (OSError, TypeError, SyntaxError) as e:
            raise _UnsupportedNode(f"Cannot parse {name!r}: {e}")
        fd = _find_funcdef(tree)
        if fd is None: raise _UnsupportedNode(f"No funcdef in {name!r}")
        ret = _return_expr(fd.body)
        if ret is None: raise _UnsupportedNode(f"No return expr in {name!r}")
        bindings = {**self.ctx.bindings}
        for arg, value in _arg_bindings(fd, call_args, call_kws).items():
            if isinstance(value, ast.Name) and value.id in self.ctx.bindings:
                value = self.ctx.bindings[value.id]
            bindings[arg] = value
        # Inlined methods always use 'self' as their record variable.
        # The outer record_var (e.g. 'move') is still accessible via bindings
        # if needed, but 'self' must map to the same table.
        ctx = _Ctx('self', self.ctx.model, self.ctx.table, bindings, self.ctx.target_type, self.ctx.depth + 1)
        return _Transpiler(ctx).to_sql(ret)

    def _pyconst(self, n) -> Any:
        """Evaluate node to a Python constant, resolving Name bindings."""
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            return [self._pyconst(e) for e in n.elts]
        if isinstance(n, ast.Name):
            pv = self._pyval(n)
            if pv is not _SENTINEL: return pv
        raise _UnsupportedNode(f"Not a compile-time constant: {ast.unparse(n)!r}")

    def _eval_api_model(self, method, call_args, call_kws):
        SQL = _S()
        try:
            pargs = [self._pyconst(a) for a in call_args]
            pkws  = {kw.arg: self._pyconst(kw.value) for kw in call_kws}
            r = method(self.ctx.model, *pargs, **pkws)
        except Exception: return None
        if isinstance(r, (list, tuple, set)):
            return SQL('(%s)', SQL(', ').join(SQL('%s', v) for v in r))
        if isinstance(r, (str, int, float, bool)):
            return SQL('%s', r)
        return None

    def _any_gen(self, gen: ast.GeneratorExp):
        from odoo.orm.domains import Domain
        if len(gen.generators) != 1: raise _UnsupportedNode("Only single-generator any() supported")
        comp = gen.generators[0]
        if not isinstance(comp.target, ast.Name): raise _UnsupportedNode("Generator target must be a name")
        loop_var = comp.target.id
        chain, base = _unroll(comp.iter)
        if not (isinstance(base, ast.Name) and base.id == self.ctx.record_var and chain):
            raise _UnsupportedNode("Generator must iterate over record fields")
        leaf_model = self.ctx.model
        for fname in chain:
            f = leaf_model._fields.get(fname)
            if f is None: raise _UnsupportedNode(f"Field {fname!r} not found on {leaf_model._name!r}")
            leaf_model = leaf_model.env[f.comodel_name]
        domain = _ast_to_domain(gen.elt, loop_var, leaf_model)
        for fname in reversed(chain):
            domain = Domain(fname, 'any', domain)
        return domain.optimize_full(self.ctx.model)._to_sql(self.ctx.table)


# ── Local variable collector ─────────────────────────────────────────────────

class _LocalCollector:
    def __init__(self, record_var, model):
        self.rv = record_var
        self.model = model
        self.bindings: dict = {}

    def collect(self, stmts):
        for s in stmts:
            if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name):
                b = self._eval(s.value)
                if b is not None:
                    self.bindings[s.targets[0].id] = b

    def _eval(self, node):
        if isinstance(node, ast.Attribute):
            chain, base = _unroll(node)
            if isinstance(base, ast.Name) and base.id == self.rv and len(chain) == 1:
                f = self.model._fields.get(chain[0])
                if f and f.type in ('one2many', 'many2many'):
                    return _VRSSpec(chain[0])
            return node
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            chain, base = _unroll(node.func)
            if isinstance(base, ast.Name) and base.id in self.bindings and len(chain) == 1:
                p = self.bindings[base.id]
                if isinstance(p, _VRSSpec):
                    return self._vrs_method(p, chain[0], node.args, node.keywords)
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            p = self.bindings.get(node.value.id)
            if isinstance(p, _VRSSpec) and _is_head_slice(node.slice):
                return dataclasses.replace(p, is_limited=True)
        return node

    def _vrs_method(self, spec, method, args, kws):
        if method == 'sorted' and args:
            try:
                key = _const(args[0])
                rev = any(kw.arg == 'reverse' and _const(kw.value) for kw in kws)
                return dataclasses.replace(spec, order_by=spec.order_by + ((key, rev),))
            except _UnsupportedNode: return None
        if method == 'filtered' and args and isinstance(args[0], ast.Lambda):
            lam = args[0]
            return dataclasses.replace(spec, filter_lambdas=spec.filter_lambdas + ((lam.args.args[0].arg, lam.body),))
        return None


def _is_head_slice(s) -> bool:
    return isinstance(s, ast.Slice) and s.lower is None and isinstance(s.upper, ast.Constant) and s.upper.value == 1


# ── Assignment extractor (with continue-guard) ───────────────────────────────

class _AssignmentExtractor:
    def __init__(self, rv, field_name):
        self.rv = rv
        self.fname = field_name

    def extract(self, stmts):
        return self._stmts(stmts, [])

    def _stmts(self, stmts, remaining):
        for i, s in enumerate(stmts):
            r = self._stmt(s, list(stmts[i+1:]) + remaining)
            if r is not None: return r
        return None

    def _stmt(self, s, remaining):
        if isinstance(s, ast.Assign) and len(s.targets) == 1:
            t = s.targets[0]
            if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                    and t.value.id == self.rv and t.attr == self.fname):
                return s.value
        if isinstance(s, ast.If):
            return self._if(s, remaining)
        return None

    def _if(self, node, remaining):
        is_guard = node.body and isinstance(node.body[-1], ast.Continue) and not node.orelse
        body_r = self._stmts(node.body[:-1] if is_guard else node.body, [])
        else_r = self._stmts(remaining, []) if is_guard else (
            self._if(node.orelse[0], remaining) if (node.orelse and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If))
            else self._stmts(node.orelse, []) if node.orelse else self._stmts(remaining, [])
        )
        if body_r is None and else_r is None: return None
        if body_r is None: return else_r
        if else_r is None: return ast.IfExp(test=node.test, body=body_r, orelse=ast.Constant(value=None))
        return ast.IfExp(test=node.test, body=body_r, orelse=else_r)


# ── Loop body extractor ──────────────────────────────────────────────────────

class _LoopBodyExtractor(ast.NodeVisitor):
    def __init__(self): self.rv = None; self.body = None

    def find(self, stmts):
        for s in stmts: self.visit(s)
        return self.rv is not None

    def visit_For(self, node):
        if (isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Name)
                and node.iter.id == 'self' and not node.orelse):
            self.rv = node.target.id; self.body = node.body
        else: self.generic_visit(node)


# ── Domain conversion for any() generator bodies ────────────────────────────

def _ast_to_domain(node: ast.expr, lvar: str, comodel):
    from odoo.orm.domains import Domain

    def _field(n):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == lvar:
            return n.attr
        return None

    if isinstance(node, ast.BoolOp):
        parts = [_ast_to_domain(v, lvar, comodel) for v in node.values]
        r = parts[0]
        for p in parts[1:]: r = r & p if isinstance(node.op, ast.And) else r | p
        return r

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return ~_ast_to_domain(node.operand, lvar, comodel)

    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        fn = _field(node.left)
        if fn:
            op = {ast.Eq:'=', ast.NotEq:'!=', ast.Lt:'<', ast.LtE:'<=',
                  ast.Gt:'>', ast.GtE:'>='}.get(type(node.ops[0]))
            if op: return Domain(fn, op, _const(node.comparators[0]))
            if isinstance(node.ops[0], ast.In):    return Domain(fn, 'in',     _seq(node.comparators[0]))
            if isinstance(node.ops[0], ast.NotIn): return Domain(fn, 'not in', _seq(node.comparators[0]))

    fn = _field(node)
    if fn:
        f = comodel._fields.get(fn)
        if f and f.type in ('char', 'text', 'html', 'selection'):
            return Domain(fn, 'not in', [False, '', None])
        return Domain(fn, '!=', False)

    raise _UnsupportedNode(f"Cannot convert {ast.unparse(node)!r} to a Domain")


# ── Method inlining helpers ──────────────────────────────────────────────────

def _find_funcdef(tree):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): return n
    return None


def _return_expr(stmts):
    for s in stmts:
        if isinstance(s, ast.Return) and s.value: return s.value
    return _stmts_to_ifexp(stmts)


def _stmts_to_ifexp(stmts):
    if not stmts: return None
    s = stmts[0]
    if isinstance(s, ast.Return) and s.value: return s.value
    if isinstance(s, ast.If):
        b = _stmts_to_ifexp(s.body)
        if b is None: return None
        e = _stmts_to_ifexp(s.orelse if s.orelse else stmts[1:])
        if e is None: return None
        return ast.IfExp(test=s.test, body=b, orelse=e)
    return None


def _arg_bindings(fd, call_args, call_kws):
    params = [a.arg for a in fd.args.args if a.arg != 'self']
    defs = fd.args.defaults
    off = len(params) - len(defs)
    b: dict = {}
    for i, a in enumerate(call_args):
        if i < len(params): b[params[i]] = a
    for kw in call_kws:
        if kw.arg: b[kw.arg] = kw.value
    for i, p in enumerate(params):
        if p not in b and (i - off) >= 0: b[p] = defs[i - off]
    return b


# ── Public API ───────────────────────────────────────────────────────────────

def _make_auto_compute_sql(compute_name: str, field_name: str, model=None) -> Callable | None:
    """Return a lazy ``(model, table) -> SQL`` callable for ``compute_sql``.

    If *model* is supplied (the BaseModel instance from ``Field.setup``), the
    compute method is parsed eagerly; returns ``None`` if any unsupported
    pattern is encountered so the caller can leave ``compute_sql`` unset.
    """
    _cache: dict = {}   # model class → transpile callable | _UnsupportedNode

    def _parse(m):
        """Parse the compute method for model class ``type(m)`` and populate cache."""
        cls = type(m)
        raw = getattr(cls, compute_name, None)
        if raw is None:
            raise _UnsupportedNode(f"Method {compute_name!r} not found on {cls._name!r}")
        try:
            src = textwrap.dedent(inspect.getsource(getattr(raw, '__wrapped__', raw)))
            tree = ast.parse(src)
        except (OSError, TypeError, SyntaxError) as e:
            raise _UnsupportedNode(f"Cannot parse {compute_name!r}: {e}")
        fd = _find_funcdef(tree)
        if fd is None: raise _UnsupportedNode(f"No funcdef in {compute_name!r}")
        ext = _LoopBodyExtractor()
        if not ext.find(fd.body):
            raise _UnsupportedNode(f"No 'for x in self:' loop in {compute_name!r}")
        coll = _LocalCollector(ext.rv, m)
        coll.collect(ext.body)
        target = _AssignmentExtractor(ext.rv, field_name).extract(ext.body)
        if target is None:
            raise _UnsupportedNode(f"No assignment to {field_name!r} in {compute_name!r}")
        spec = (ext.rv, coll.bindings, target)

        def _transpile(m_, t_):
            ctx = _Ctx(spec[0], m_, t_, dict(spec[1]), m_._fields[field_name].type)
            try:
                return _Transpiler(ctx)._value_sql(spec[2])
            except _UnsupportedNode as e:
                raise ValueError(f"compute_sql derivation failed for {field_name!r}: {e}") from e

        _cache[cls] = _transpile
        return _transpile

    # Eager validation at field-setup time
    if model is not None:
        try:
            _parse(model)
        except _UnsupportedNode as e:
            _logger.debug("auto compute_sql skipped for %r in %r: %s",
                          field_name, compute_name, e)
            return None

    def _auto_compute_sql(m, t):
        cls = type(m)
        fn = _cache.get(cls)
        if fn is None:
            try: fn = _parse(m)
            except _UnsupportedNode as e:
                raise ValueError(f"compute_sql derivation failed for {field_name!r}: {e}") from e
        elif isinstance(fn, _UnsupportedNode):
            raise ValueError(f"compute_sql derivation failed for {field_name!r}: {fn}") from fn
        return fn(m, t)

    _auto_compute_sql.__name__ = f'_auto_compute_sql__{field_name}'
    return _auto_compute_sql
