from __future__ import annotations

import ast
import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, NamedTuple

from lxml import etree
from psycopg.types.json import Json

from odoo.db.schema import (
    column_exists,
    get_table_columns,
    get_tables_existing,
    rename_column,
    table_exists,
)
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL

if TYPE_CHECKING:
    from typing import Any, Protocol

    from odoo.db import BaseCursor

    class _SqlCursor(Protocol):
        """The four members these helpers touch.

        Narrower than `BaseCursor` on purpose: a migration script or a test can hand
        them anything that answers SQL, which is how `tests/test_module_data.py`
        exercises the statements without a database.
        """

        @property
        def rowcount(self) -> int: ...
        def execute(self, query: Any, params: Any = None) -> Any: ...
        def fetchall(self) -> list[tuple[Any, ...]]: ...
        def fetchone(self) -> tuple[Any, ...] | None: ...


_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def adopt_xmlids(
    cr: _SqlCursor,
    from_module: str,
    to_module: str,
    names: Iterable[str],
    renamed: Mapping[str, str] | None = None,
) -> int:
    pairs = {
        old: new or old
        for old, new in {**dict.fromkeys(names), **(renamed or {})}.items()
    }
    if not pairs:
        return 0
    olds, news = list(pairs), list(pairs.values())
    cr.execute(
        SQL(
            """
            SELECT source.id, source.name, target.name,
                   source.model = target.model AND source.res_id = target.res_id
              FROM unnest(%s::varchar[], %s::varchar[]) AS pair(old, new)
              JOIN ir_model_data source
                ON source.module = %s AND source.name = pair.old
              JOIN ir_model_data target
                ON target.module = %s AND target.name = pair.new
             WHERE source.id != target.id
            """,
            olds,
            news,
            from_module,
            to_module,
        )
    )
    clashes = cr.fetchall()
    if conflicting := sorted(
        f"{old} -> {new}" for _id, old, new, same in clashes if not same
    ):
        raise ValueError(
            f"{to_module} already names other records {conflicting}; "
            f"{from_module}'s xml ids cannot take those names"
        )
    # the name is already the record's under the adopting module: the old
    # xml id is a duplicate, and dropping it is the adoption
    if duplicates := [row_id for row_id, *_names, _same in clashes]:
        cr.execute(SQL("DELETE FROM ir_model_data WHERE id = ANY(%s)", duplicates))
    cr.execute(
        SQL(
            """
            UPDATE ir_model_data data SET module = %s, name = pair.new
              FROM unnest(%s::varchar[], %s::varchar[]) AS pair(old, new)
             WHERE data.module = %s AND data.name = pair.old
            """,
            to_module,
            olds,
            news,
            from_module,
        )
    )
    moved = cr.rowcount + len(duplicates)
    _debug.lifecycle(
        "module_data.xmlids_adopted",
        from_module=from_module,
        to_module=to_module,
        requested=len(pairs),
        moved=moved,
        duplicates=len(duplicates),
    )
    if moved:
        _logger.info("%s adopted %d record(s) from %s", to_module, moved, from_module)
    return moved


# the models whose `_table` is not their name with dots for underscores; a
# pre-migration of base runs before any registry holds them
_MODEL_TABLES: Mapping[str, str] = {
    "ir.actions.actions": "ir_actions",
    "ir.actions.act_window": "ir_act_window",
    "ir.actions.act_window.view": "ir_act_window_view",
    "ir.actions.act_window_close": "ir_act_window_close",
    "ir.actions.act_url": "ir_act_url",
    "ir.actions.server": "ir_act_server",
    "ir.actions.client": "ir_act_client",
    "ir.actions.report": "ir_act_report_xml",
}


def _table_of(model: str) -> str:
    return _MODEL_TABLES.get(model) or model.replace(".", "_")


def remove_xmlid_records(cr: BaseCursor, module: str, names: Iterable[str]) -> int:
    names = list(names)
    cr.execute(
        SQL(
            """
            SELECT d.id, d.model, d.res_id, EXISTS (
                   SELECT 1 FROM ir_model_data other
                    WHERE other.model = d.model AND other.res_id = d.res_id
                      AND other.module != d.module)
              FROM ir_model_data d
             WHERE d.module = %s AND d.name = ANY(%s)
            """,
            module,
            names,
        )
    )
    # a record another module also names lives on under that name: only this
    # module's xml id goes
    released: list[int] = []
    by_model: dict[str, dict[int, int]] = defaultdict(dict)
    for data_id, model, res_id, shared in cr.fetchall():
        if shared:
            released.append(data_id)
        else:
            by_model[model][res_id] = data_id
    existing = set(get_tables_existing(cr, [_table_of(model) for model in by_model]))
    deleted = 0
    for model, records in by_model.items():
        table = _table_of(model)
        if table not in existing:
            cr.execute(SQL("SELECT 1 FROM ir_model WHERE model = %s", model))
            registered = bool(cr.fetchone())
            _debug.logic(
                "module_data.records_table_missing",
                module=module,
                model=model,
                records=len(records),
                registered=registered,
            )
            if registered:
                # the model is live and its table is not where the name puts
                # it: deleting the xml ids would orphan records nobody deleted
                _logger.warning(
                    "%s: kept %d xml id(s) of %s, whose records are not in a table "
                    "named %s; they were not deleted",
                    module,
                    len(records),
                    model,
                    table,
                )
                continue
            released.extend(records.values())
            continue
        cr.execute(
            SQL(
                "DELETE FROM %s WHERE id = ANY(%s)",
                SQL.identifier(table),
                list(records),
            )
        )
        deleted += cr.rowcount
        # a DELETE either removes the row or raises: an id it did not remove
        # was already gone, and its xml id dangles
        released.extend(records.values())
    cr.execute(SQL("DELETE FROM ir_model_data WHERE id = ANY(%s)", released))
    _debug.lifecycle(
        "module_data.xmlid_records_removed",
        module=module,
        models=sorted(by_model),
        deleted=deleted,
        xmlids=cr.rowcount,
    )
    return deleted


def retire_empty_module(cr: _SqlCursor, module: str) -> None:
    cr.execute(SQL("SELECT 1 FROM ir_model_data WHERE module = %s LIMIT 1", module))
    if cr.fetchone():
        _debug.logic("module_data.module_kept", module=module, reason="has_xmlids")
        return
    cr.execute(
        SQL(
            "UPDATE ir_module_module SET state = 'uninstalled', db_version = NULL "
            "WHERE name = %s AND state != 'uninstalled'",
            module,
        )
    )
    retired = cr.rowcount > 0
    # Also for a row already uninstalled: the module is gone from disk, and a
    # leftover auto_install makes the loader mark it `to install` the day its
    # dependencies happen to be installed, which ends the upgrade in an
    # inconsistent state naming a module nobody can supply.
    cr.execute(
        SQL(
            "UPDATE ir_module_module SET auto_install = FALSE "
            "WHERE name = %s AND auto_install",
            module,
        )
    )
    cr.execute(
        SQL(
            "DELETE FROM ir_module_module_dependency "
            "WHERE module_id = (SELECT id FROM ir_module_module WHERE name = %s)",
            module,
        )
    )
    _debug.lifecycle("module_data.module_retired", module=module, retired=retired)
    if retired:
        _logger.info("%s retired: every record it shipped now lives elsewhere", module)


def rename_module(cr: BaseCursor, old: str, new: str) -> bool:
    cr.execute(SQL("SELECT id FROM ir_module_module WHERE name = %s", old))
    if not cr.fetchone():
        return False
    _drop_uninstalled_placeholder(cr, old, new)
    cr.execute(
        SQL(
            "UPDATE ir_module_module SET name = %s, data_file_checksums = NULL "
            "WHERE name = %s",
            new,
            old,
        )
    )
    for table in ("ir_module_module_dependency", "ir_module_module_exclusion"):
        cr.execute(
            SQL(
                """
                DELETE FROM %(table)s stale
                      WHERE stale.name = %(old)s
                        AND EXISTS (SELECT 1 FROM %(table)s kept
                                     WHERE kept.module_id = stale.module_id
                                       AND kept.name = %(new)s)
                """,
                table=SQL.identifier(table),
                old=old,
                new=new,
            )
        )
        cr.execute(
            SQL(
                "UPDATE %s SET name = %s WHERE name = %s",
                SQL.identifier(table),
                new,
                old,
            )
        )
    moved = _rename_module_xmlids(cr, old, new)
    cr.execute(
        SQL(
            """
            UPDATE ir_config_parameter
               SET key = %(new)s || substring(key from %(tail)s)
             WHERE key LIKE %(like)s
               AND NOT EXISTS (
                   SELECT 1 FROM ir_config_parameter existing
                    WHERE existing.key = %(new)s || substring(ir_config_parameter.key from %(tail)s)
               )
            """,
            new=f"{new}.",
            tail=len(old) + 2,
            like=_like_prefix(f"{old}."),
        )
    )
    _rename_module_references(cr, old, new)
    cr.execute(
        SQL(
            "UPDATE ir_ui_view SET key = %s || substring(key from %s) WHERE key LIKE %s",
            f"{new}.",
            len(old) + 2,
            _like_prefix(f"{old}."),
        )
    )
    for table, column in (
        ("ir_asset", "path"),
        ("ir_asset", "target"),
        ("ir_ui_view", "arch_fs"),
    ):
        if column_exists(cr, table, column):
            cr.execute(
                SQL(
                    "UPDATE %s SET %s = regexp_replace(%s, %s, %s) WHERE %s ~ %s",
                    SQL.identifier(table),
                    SQL.identifier(column),
                    SQL.identifier(column),
                    f"^(/?){old}/",
                    rf"\1{new}/",
                    SQL.identifier(column),
                    f"^/?{old}/",
                )
            )
    if column_exists(cr, "ir_asset", "bundle"):
        cr.execute(
            SQL(
                "UPDATE ir_asset SET bundle = %s || substring(bundle from %s) "
                "WHERE bundle LIKE %s",
                f"{new}.",
                len(old) + 2,
                _like_prefix(f"{old}."),
            )
        )
    _debug.lifecycle("module_data.module_renamed", old=old, new=new, xmlids=moved)
    _logger.info("renamed module %s to %s with %s xml id(s)", old, new, moved)
    return True


def _drop_uninstalled_placeholder(cr: _SqlCursor, old: str, new: str) -> None:
    cr.execute(SQL("SELECT id, state FROM ir_module_module WHERE name = %s", new))
    if not (row := cr.fetchone()):
        return
    module_id, state = row
    if state != "uninstalled":
        raise ValueError(
            f"{old} and {new} are both present and {new} is {state}; "
            f"uninstall {new}, then upgrade base again"
        )
    cr.execute(
        SQL(
            "DELETE FROM ir_model_data WHERE module = 'base' "
            "AND model = 'ir.module.module' AND res_id = %s",
            module_id,
        )
    )
    for table in ("ir_module_module_dependency", "ir_module_module_exclusion"):
        cr.execute(
            SQL("DELETE FROM %s WHERE module_id = %s", SQL.identifier(table), module_id)
        )
    cr.execute(SQL("DELETE FROM ir_module_module WHERE id = %s", module_id))
    _logger.info("dropped the uninstalled %s placeholder", new)


def _rename_module_xmlids(cr: _SqlCursor, old: str, new: str) -> int:
    cr.execute(
        SQL(
            """
            SELECT d.name FROM ir_model_data d
             WHERE d.module = %s
               AND EXISTS (SELECT 1 FROM ir_model_data o
                            WHERE o.module = %s AND o.name = d.name)
            """,
            old,
            new,
        )
    )
    if clashing := sorted(name for (name,) in cr.fetchall()):
        raise ValueError(f"{old} and {new} both own {clashing}")
    cr.execute(SQL("UPDATE ir_model_data SET module = %s WHERE module = %s", new, old))
    moved = cr.rowcount
    cr.execute(
        SQL(
            "UPDATE ir_model_data SET name = %s "
            "WHERE module = 'base' AND model = 'ir.module.module' AND name = %s",
            f"module_{new}",
            f"module_{old}",
        )
    )
    return moved


def _like_prefix(prefix: str) -> str:
    return prefix.replace("_", "\\_") + "%"


READONLY_FORERUNNERS: Mapping[str, str] = {
    "stock_group_readonly": "stock",
    "sale_group_readonly": "sale",
    "purchase_group_readonly": "purchase",
    "mrp_group_readonly": "mrp",
}
READONLY_MERGED_MODULE = "group_readonly"
_ACCESS_PREFIX = "access_"
_READONLY_SUFFIX = "_readonly"


def _readonly_merged_name(name: str, domain: str) -> str:
    if name.startswith(_ACCESS_PREFIX) and name.endswith(_READONLY_SUFFIX):
        return f"{name[: -len(_READONLY_SUFFIX)]}_{domain}{_READONLY_SUFFIX}"
    return name


def absorb_readonly_forerunners(cr: _SqlCursor) -> int:
    moved = 0
    for module, domain in READONLY_FORERUNNERS.items():
        cr.execute(SQL("SELECT id, name FROM ir_model_data WHERE module = %s", module))
        rows = cr.fetchall()
        for row_id, name in rows:
            cr.execute(
                SQL(
                    "UPDATE ir_model_data SET module = %s, name = %s WHERE id = %s",
                    READONLY_MERGED_MODULE,
                    _readonly_merged_name(name, domain),
                    row_id,
                )
            )
        moved += len(rows)
        if rows:
            _logger.info(
                "%s absorbed %d record(s) from %s",
                READONLY_MERGED_MODULE,
                len(rows),
                module,
            )
            retire_empty_module(cr, module)
    return moved


_XMLID_CALL = (
    r"\b(?:ref|_xmlid_to_res_id|_xmlid_to_res_model_res_id|_xmlid_lookup)\(\s*"
)
_XMLID_ATTRIBUTES = frozenset({"t-call", "t-call-assets", "t-snippet"})


class _ModuleRename:
    # A module's name as it stands in stored data: the prefix of an xml id in
    # the positions that hold one, and nowhere else, since `sale_team.` also
    # opens model names (`env['iot.box']`) that no module rename touches.
    def __init__(self, old: str, new: str) -> None:
        self.old = old
        self.new = new
        module = re.escape(old)
        self.text = re.compile(
            rf"(?P<lead>{_XMLID_CALL}['\"]|%\(|\bt-call(?:-assets)?\s*=\s*['\"])"
            rf"{module}\.(?=\w)"
        )
        self.lead = re.compile(rf"^(?P<lead>\s*){module}\.(?=\w)")
        self.items = re.compile(rf"(?P<lead>(?:^|,)\s*!?\s*){module}\.(?=\w)")
        self.action = re.compile(rf"{module}\.\w[\w.]*")

    def in_text(self, value: str) -> str:
        return self.text.sub(lambda m: f"{m['lead']}{self.new}.", value)

    def in_attribute(self, element, attribute: str, value: str) -> str:
        if attribute == "groups":
            return self.items.sub(lambda m: f"{m['lead']}{self.new}.", value)
        if attribute in _XMLID_ATTRIBUTES:
            return self.lead.sub(lambda m: f"{m['lead']}{self.new}.", value)
        if attribute == "t-install":
            return self.new if value.strip() == self.old else value
        if (
            element.tag == "button"
            and attribute == "name"
            and element.get("type") == "action"
            and self.action.fullmatch(value)
        ):
            return f"{self.new}{value[len(self.old) :]}"
        return self.in_text(value)

    def in_arch(self, value: str) -> str:
        if not value or self.old not in value:
            return value
        try:
            root = etree.fromstring(value.encode())
        except etree.XMLSyntaxError:
            _debug.logic("module_data.arch_unparsed", old=self.old, model=None)
            return value
        renamed = False
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            for attribute, text in element.attrib.items():
                target = attribute
                if element.tag == "attribute" and attribute in ("add", "remove"):
                    target = element.get("name") or ""
                rewritten = self.in_attribute(element, target, text)
                if rewritten != text:
                    element.set(attribute, rewritten)
                    renamed = True
            if element.tag == "attribute" and element.text:
                rewritten = self.in_attribute(
                    element, element.get("name") or "", element.text
                )
                if rewritten != element.text:
                    element.text = rewritten
                    renamed = True
        return etree.tostring(root, encoding="unicode") if renamed else value


def _rename_module_references(cr: BaseCursor, old: str, new: str) -> int:
    rename = _ModuleRename(old, new)
    needle = f"{old}."
    rewritten = 0
    if table_exists(cr, "ir_ui_view"):
        cr.execute(
            SQL(
                "SELECT id, arch_db FROM ir_ui_view WHERE position(%s in arch_db::text) > 0",
                old,
            )
        )
        for view_id, arch in cr.fetchall():
            translations = {
                lang: rename.in_arch(value) for lang, value in (arch or {}).items()
            }
            if translations != (arch or {}):
                cr.execute(
                    SQL(
                        "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s",
                        Json(translations),
                        view_id,
                    )
                )
                rewritten += 1
    tables = set(
        get_tables_existing(cr, [source.table for source in _EXPRESSION_SOURCES])
    )
    for source in _EXPRESSION_SOURCES:
        if source.table not in tables:
            continue
        columns = _existing_columns(cr, source.table, source.columns)
        if not columns:
            continue
        cr.execute(
            SQL(
                "SELECT id, %s FROM %s WHERE %s",
                SQL(", ").join(SQL.identifier(column) for column in columns),
                SQL.identifier(source.table),
                SQL(" OR ").join(
                    SQL("position(%s in %s::text) > 0", needle, SQL.identifier(column))
                    for column in columns
                ),
            )
        )
        for row_id, *values in cr.fetchall():
            changes = {}
            for column, value in zip(columns, values, strict=True):
                if isinstance(value, dict):
                    renamed = {
                        lang: rename.in_text(text) if text else text
                        for lang, text in value.items()
                    }
                    if renamed != value:
                        changes[column] = Json(renamed)
                elif value and (renamed := rename.in_text(value)) != value:
                    changes[column] = renamed
            if not changes:
                continue
            cr.execute(
                SQL(
                    "UPDATE %s SET %s WHERE id = %s",
                    SQL.identifier(source.table),
                    SQL(", ").join(
                        SQL("%s = %s", SQL.identifier(column), value)
                        for column, value in changes.items()
                    ),
                    row_id,
                )
            )
            rewritten += 1
    _debug.perf.count(
        "module_data.module_references_rewritten", old=old, new=new, rows=rewritten
    )
    return rewritten


class _Source(NamedTuple):
    table: str
    columns: tuple[str, ...]
    scope_column: str
    scope_is_id: bool
    jsonb: frozenset[str] = frozenset()
    # columns holding domains and field paths read from the row's model, where
    # a name after a dot is a field of another model; the rest is Python over
    # variables (`record.x`, `object.x`) whose model nothing states
    paths: frozenset[str] = frozenset()


_EXPRESSION_SOURCES = (
    _Source(
        "mail_template",
        (
            "body_html",
            "subject",
            "email_from",
            "email_to",
            "email_cc",
            "partner_to",
            "reply_to",
            "scheduled_date",
        ),
        "model_id",
        True,
        jsonb=frozenset({"body_html", "subject"}),
    ),
    _Source("ir_act_server", ("code",), "model_id", True),
    _Source(
        "ir_filters",
        ("domain", "context", "sort"),
        "model_id",
        False,
        paths=frozenset({"domain", "context", "sort"}),
    ),
    _Source(
        "ir_act_window",
        ("domain", "context"),
        "res_model",
        False,
        paths=frozenset({"domain", "context"}),
    ),
    _Source(
        "ir_rule",
        ("domain_force",),
        "model_id",
        True,
        paths=frozenset({"domain_force"}),
    ),
    _Source(
        "base_automation",
        ("filter_domain", "filter_pre_domain"),
        "model_id",
        True,
        paths=frozenset({"filter_domain", "filter_pre_domain"}),
    ),
    _Source(
        "ir_embedded_actions",
        ("domain", "context", "python_method"),
        "parent_res_model",
        False,
        paths=frozenset({"domain", "context"}),
    ),
)

_EXPRESSION_ATTRIBUTES = frozenset(
    {
        "attrs",
        "column_invisible",
        "context",
        "domain",
        "eval",
        "filter_domain",
        "invisible",
        "options",
        "readonly",
        "required",
        "t-elif",
        "t-esc",
        "t-field",
        "t-foreach",
        "t-if",
        "t-out",
        "t-value",
    }
)
_DOMAIN_ATTRIBUTES = frozenset({"attrs", "domain", "filter_domain"})
_UNKNOWN_MODEL = object()


def _existing_columns(cr: BaseCursor, table: str, columns: Iterable[str]) -> list[str]:
    return [column for column in columns if column_exists(cr, table, column)]


class _FieldRename:
    # One field renamed on one model (`model` None: wherever the name is read),
    # with the relational graph a pre-migration reads from ir_model_fields.
    def __init__(
        self,
        old: str,
        new: str,
        model: str | None,
        comodels: Mapping[tuple[str, str], str],
    ) -> None:
        self.old = old
        self.new = new
        self.model = model
        self.comodels = comodels
        self.word = re.compile(r"\b%s\b" % re.escape(old))
        self.first = re.compile(r"(?<![\w.])%s\b" % re.escape(old))
        # a field of one model, spelled bare: every read of it is resolved to
        # a model before it is renamed; anything else keeps the word rewrite
        self.precise = model is not None and "." not in old

    def comodel(self, model: Any, name: str | None) -> Any:
        if model is _UNKNOWN_MODEL or not name:
            return _UNKNOWN_MODEL
        found = self.comodels.get((model, name))
        # the field row may already carry either spelling, depending on whether
        # rename_field ran first
        if found is None and name in (self.old, self.new):
            other = self.new if name == self.old else self.old
            found = self.comodels.get((model, other))
        return _UNKNOWN_MODEL if found is None else found

    def is_target(self, model: Any) -> bool:
        return self.model is None or model == self.model

    def rename_path(self, path: str, root: Any, separator: str = ".") -> str:
        current = root
        segments = []
        for segment in path.split(separator):
            segments.append(
                self.new if segment == self.old and current == self.model else segment
            )
            current = self.comodel(current, segment)
        return separator.join(segments)

    def expression(
        self,
        source: str,
        *,
        names: Any,
        strings: Any,
        parent: Any = _UNKNOWN_MODEL,
        leaves: Any = None,
    ) -> str:
        if self.old not in source:
            return source
        edits = _ExpressionEdits(self, names, strings, parent, leaves).run(source)
        if edits is None:
            _debug.logic("module_data.expression_unparsed", old=self.old)
            return self.first.sub(self.new, source) if strings == self.model else source
        return edits


class _ExpressionEdits:
    # Rewrites one Python expression by the spans its AST gives, so a name is
    # renamed only where it reads a field of the renamed model: a bare name
    # reads `names`, `parent.x` reads `parent`, `a.b` reads b on a's comodel, a
    # domain leaf's path walks from `leaves`, and a string elsewhere
    # (`'group_by': 'user_id'`) names a field of `strings` by its first segment.
    def __init__(
        self, rename: _FieldRename, names: Any, strings: Any, parent: Any, leaves: Any
    ) -> None:
        self.rename = rename
        self.names = names
        self.strings = strings
        self.parent = parent
        self.leaves = leaves
        self.edits: list[tuple[int, int, bytes]] = []
        self.source = b""
        self.starts: list[int] = []

    def run(self, source: str) -> str | None:
        # parenthesised, an expression may start indented or span lines
        wrapped = f"({source}\n)"
        try:
            tree = ast.parse(wrapped, mode="eval")
        except SyntaxError, ValueError:
            return None
        self.source = wrapped.encode()
        self.starts = [0]
        for line in self.source.splitlines(keepends=True):
            self.starts.append(self.starts[-1] + len(line))
        self.visit(tree.body)
        if not self.edits:
            return source
        out = self.source
        for start, end, text in sorted(self.edits, reverse=True):
            out = out[:start] + text + out[end:]
        return out.decode()[1:-2]

    def span(self, node: ast.expr) -> tuple[int, int]:
        assert node.end_lineno is not None and node.end_col_offset is not None
        return (
            self.starts[node.lineno - 1] + node.col_offset,
            self.starts[node.end_lineno - 1] + node.end_col_offset,
        )

    def visit(self, node: ast.AST) -> None:
        rename = self.rename
        if isinstance(node, ast.Name):
            if node.id == rename.old and self.names == rename.model:
                start, end = self.span(node)
                self.edits.append((start, end, rename.new.encode()))
        elif isinstance(node, ast.Attribute):
            self.visit_attribute(node)
        elif self.leaves is not None and _is_leaf(node):
            assert isinstance(node, (ast.List, ast.Tuple))
            path = node.elts[0]
            assert isinstance(path, ast.Constant)
            self.literal(path, rename.rename_path(path.value, self.leaves))
            for value in node.elts[1:]:
                if not isinstance(value, ast.Constant):
                    self.visit(value)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str) and self.strings == rename.model:
                self.literal(node, rename.first.sub(rename.new, node.value))
        else:
            for child in ast.iter_child_nodes(node):
                self.visit(child)

    def visit_attribute(self, node: ast.Attribute) -> None:
        rename = self.rename
        chain = []
        base: ast.expr = node
        while isinstance(base, ast.Attribute):
            chain.append(base)
            base = base.value
        if not isinstance(base, ast.Name):
            self.visit(base)
            return
        if base.id == "parent":
            current = self.parent
        else:
            self.visit(base)
            current = rename.comodel(self.names, base.id)
        for link in reversed(chain):
            if link.attr == rename.old and current == rename.model:
                _start, end = self.span(link)
                self.edits.append((end - len(link.attr), end, rename.new.encode()))
            current = rename.comodel(current, link.attr)

    def literal(self, node: ast.Constant, value: str) -> None:
        if value == node.value:
            return
        start, end = self.span(node)
        raw = self.source[start:end].decode()
        quote = raw[:1]
        # a prefixed, escaped or triple-quoted literal is not rebuilt by hand
        if quote not in ("'", '"') or raw != f"{quote}{node.value}{quote}":
            _debug.logic("module_data.literal_kept", literal=raw)
            return
        self.edits.append((start, end, f"{quote}{value}{quote}".encode()))


def _is_leaf(node: ast.AST) -> bool:
    return (
        isinstance(node, (ast.List, ast.Tuple))
        and len(node.elts) == 3
        and isinstance(node.elts[0], ast.Constant)
        and isinstance(node.elts[0].value, str)
    )


def rename_in_view_arches(
    cr: BaseCursor, old: str, new: str, *, model: str | None = None
) -> int:
    # A view's nested subviews describe their comodel, not the view's model, so a
    # rewrite scoped by ir_ui_view.model alone renames a namesake of the comodel
    # and misses the subview nodes that do belong to `model`.
    if not table_exists(cr, "ir_ui_view"):
        return 0
    cr.execute(
        SQL(
            "SELECT 1 FROM ir_ui_view WHERE arch_db::text ~ %s LIMIT 1",
            r"\y%s\y" % old.replace(".", r"\."),
        )
    )
    if not cr.fetchone():
        return 0
    return _rename_in_views(cr, _FieldRename(old, new, model, _relational_comodels(cr)))


def _rename_in_views(cr: BaseCursor, rename: _FieldRename) -> int:
    if not table_exists(cr, "ir_ui_view"):
        return 0
    cr.execute(
        SQL(
            "SELECT id, model, arch_db FROM ir_ui_view WHERE arch_db::text ~ %s",
            r"\y%s\y" % rename.old.replace(".", r"\."),
        )
    )
    rewritten = 0
    for view_id, view_model, arch in cr.fetchall():
        translations = {
            lang: _rename_in_arch(value, view_model, rename)
            for lang, value in (arch or {}).items()
        }
        if translations == (arch or {}):
            continue
        cr.execute(
            SQL(
                "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s",
                Json(translations),
                view_id,
            )
        )
        rewritten += 1
    _debug.perf.count(
        "module_data.view_arches_rewritten",
        old=rename.old,
        new=rename.new,
        model=rename.model,
        rows=rewritten,
    )
    return rewritten


def _relational_comodels(cr: BaseCursor) -> dict[tuple[str, str], str]:
    cr.execute(
        SQL(
            "SELECT model, name, relation FROM ir_model_fields "
            "WHERE relation IS NOT NULL AND ttype IN ('many2one', 'one2many', 'many2many')"
        )
    )
    return {(model, name): relation for model, name, relation in cr.fetchall()}


def _rename_in_arch(value: str, view_model: Any, rename: _FieldRename) -> str:
    if not value or rename.old not in value:
        return value
    try:
        root = etree.fromstring(value.encode())
    except etree.XMLSyntaxError:
        _debug.logic("module_data.arch_unparsed", old=rename.old, model=rename.model)
        return value
    if not _rename_in_node(root, _Scope(view_model), rename):
        return value
    return etree.tostring(root, encoding="unicode")


class _Scope(NamedTuple):
    # the model a node's field names read, the model `parent.` reads there, and,
    # for the <attribute> children of a `position="attributes"` locator, the
    # comodel of the field it locates (a domain set there is that comodel's)
    model: Any
    parent: Any = _UNKNOWN_MODEL
    located: Any = _UNKNOWN_MODEL


def _rename_in_node(node, scope: _Scope, rename: _FieldRename) -> bool:
    renamed = False
    in_scope = rename.is_target(scope.model)
    for attribute, value in node.attrib.items():
        if not value or rename.old not in value:
            continue
        if attribute == "expr":
            rewritten = _rename_in_xpath(value, scope, rename)[0]
        elif attribute in ("name", "for") and node.tag in ("field", "label"):
            rewritten = rename.new if in_scope and value == rename.old else value
        elif attribute in _EXPRESSION_ATTRIBUTES or attribute.startswith("decoration-"):
            rewritten = _rename_in_attribute(node, attribute, value, scope, rename)
        else:
            continue
        if rewritten != value:
            node.set(attribute, rewritten)
            renamed = True
    name = node.get("name") or ""
    if (
        node.tag == "attribute"
        and node.text
        and rename.old in node.text
        and (name in _EXPRESSION_ATTRIBUTES or name.startswith("decoration-"))
    ):
        rewritten = _rename_in_attribute(node, name, node.text, scope, rename)
        if rewritten != node.text:
            node.text = rewritten
            renamed = True
    for child in node:
        renamed |= _rename_in_node(child, _child_scope(node, scope, rename), rename)
    return renamed


def _rename_in_attribute(node, attribute, value, scope: _Scope, rename: _FieldRename):
    if not rename.precise or attribute.startswith("t-") or attribute == "eval":
        # a QWeb expression reads variables (`partner.comment`) whose model no
        # attribute states: the word rewrite, on the nodes of the model
        if not rename.is_target(scope.model):
            return value
        return rename.word.sub(rename.new, value)
    leaves = None
    if attribute in _DOMAIN_ATTRIBUTES:
        leaves = scope.model
        if attribute == "domain":
            if node.tag == "field":
                leaves = rename.comodel(scope.model, node.get("name"))
            elif node.tag == "attribute":
                leaves = scope.located
    return rename.expression(
        value,
        names=scope.model,
        strings=scope.model,
        parent=scope.parent,
        leaves=leaves,
    )


def _child_scope(node, scope: _Scope, rename: _FieldRename) -> _Scope:
    position = node.get("position") or "inside"
    inner = position == "inside" or (
        position == "replace" and node.get("mode") == "inner"
    )
    if node.tag == "xpath":
        _expr, around, inside = _rename_in_xpath(
            node.get("expr") or "", scope, rename, rewrite=False
        )
        if inner:
            return inside
        if position == "attributes":
            return around._replace(located=inside.model)
        return around
    if node.tag == "field" and len(node):
        # a locator placing nodes beside the field, or setting its attributes,
        # stays in the model the field sits in; its content is the comodel's
        comodel = rename.comodel(scope.model, node.get("name"))
        if inner:
            return _Scope(comodel, scope.model)
        if position == "attributes":
            return _Scope(scope.model, scope.parent, comodel)
    return _Scope(scope.model, scope.parent)


_XPATH_NAME = re.compile(r"@name\s*=\s*'([^']*)'|@name\s*=\s*\"([^\"]*)\"")


def _rename_in_xpath(
    expr: str, scope: _Scope, rename: _FieldRename, *, rewrite: bool = True
) -> tuple[str, _Scope, _Scope]:
    # `//field[@name='invoice_line_ids']//field[@name='account_id']` walks into the
    # subview: each component naming a relational field of the model reached so far
    # moves the scope to its comodel. A node placed before, after or in place of the
    # anchor is a sibling, so it belongs to the model the anchor itself sits in.
    around = current = _Scope(scope.model, scope.parent)
    pieces = []
    last = 0
    for match in _XPATH_NAME.finditer(expr):
        name = match.group(1) if match.group(1) is not None else match.group(2)
        start, end = match.span(1) if match.group(1) is not None else match.span(2)
        if rewrite and name == rename.old and rename.is_target(current.model):
            pieces.append(expr[last:start])
            pieces.append(rename.new)
            last = end
        around = current
        nested = rename.comodel(current.model, name)
        if nested is not _UNKNOWN_MODEL:
            current = _Scope(nested, current.model)
    pieces.append(expr[last:])
    return "".join(pieces), around, current


_RENAMEABLE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_.]*\Z")
_REPLACEMENT = re.compile(r"\A[A-Za-z_][A-Za-z0-9_.()]*\Z")


def rename_in_stored_expressions(
    cr: BaseCursor,
    old: str,
    new: str,
    *,
    model: str | None = None,
    unique: bool = False,
) -> int:
    # A record rule or filter reaches a renamed field through a path from its own
    # model (`user_id.crm_team_ids`), so scoping to the field's model misses it;
    # `unique` asserts no other model has a field of that name.
    if not _RENAMEABLE.match(old) or not _REPLACEMENT.match(new):
        raise ValueError(f"cannot rewrite {old!r} to {new!r}: unsupported characters")
    if old.endswith("."):
        raise ValueError(
            f"{old!r} is a module prefix: a word rewrite of it renames model names "
            "too, and rename_module rewrites the xml ids that carry it"
        )
    if model is None and "." not in old and not unique:
        raise ValueError(f"{old!r} is a bare field name and needs model= to scope it")

    rename = _FieldRename(old, new, model, _relational_comodels(cr))
    rewritten = _rename_in_views(cr, rename)
    tables = set(
        get_tables_existing(cr, [source.table for source in _EXPRESSION_SOURCES])
    )
    for source in _EXPRESSION_SOURCES:
        if source.table not in tables:
            continue
        columns = _existing_columns(cr, source.table, source.columns)
        paths = [c for c in columns if c in source.paths] if rename.precise else []
        words = [c for c in columns if c not in paths]
        count = 0
        if words:
            count += _rename_words(cr, source, words, rename)
        if paths:
            count += _rename_paths(cr, source, paths, rename)
        rewritten += count
        _debug.perf.count(
            "module_data.expressions_rewritten",
            table=source.table,
            old=old,
            new=new,
            model=model,
            rows=count,
        )
    if rename.precise or unique:
        rewritten += _rename_in_export_lines(cr, rename)
    if rewritten:
        _logger.info(
            "renamed %s to %s in %d stored expression(s)%s",
            old,
            new,
            rewritten,
            f" of {model}" if model else "",
        )
    return rewritten


def _rename_words(
    cr: BaseCursor, source: _Source, columns: list[str], rename: _FieldRename
) -> int:
    pattern = r"\y%s\y" % rename.old.replace(".", r"\.")
    scope = SQL("")
    if rename.model is not None:
        scope = SQL(
            " AND %s = (SELECT id FROM ir_model WHERE model = %s)"
            if source.scope_is_id
            else " AND %s = %s",
            SQL.identifier(source.scope_column),
            rename.model,
        )
    assignments = SQL(", ").join(
        SQL(
            "%s = regexp_replace(%s::text, %s, %s, 'g')%s",
            SQL.identifier(column),
            SQL.identifier(column),
            pattern,
            rename.new,
            SQL("::jsonb") if column in source.jsonb else SQL(""),
        )
        for column in columns
    )
    guard = SQL(" OR ").join(
        SQL("%s::text ~ %s", SQL.identifier(column), pattern) for column in columns
    )
    cr.execute(
        SQL(
            "UPDATE %s SET %s WHERE (%s)%s",
            SQL.identifier(source.table),
            assignments,
            guard,
            scope,
        )
    )
    return cr.rowcount


def _rename_paths(
    cr: BaseCursor, source: _Source, columns: list[str], rename: _FieldRename
) -> int:
    # Every row that spells the name, whatever its model: a domain on another
    # model reaches the renamed field through a path, and each path is walked
    # from the row's own model to tell whose field a segment is.
    pattern = r"\y%s\y" % rename.old
    row_model = (
        SQL(
            "(SELECT model FROM ir_model WHERE id = %s)",
            SQL.identifier(source.scope_column),
        )
        if source.scope_is_id
        else SQL.identifier(source.scope_column)
    )
    cr.execute(
        SQL(
            "SELECT id, %s, %s FROM %s WHERE %s",
            row_model,
            SQL(", ").join(SQL.identifier(column) for column in columns),
            SQL.identifier(source.table),
            SQL(" OR ").join(
                SQL("%s ~ %s", SQL.identifier(column), pattern) for column in columns
            ),
        )
    )
    rewritten = 0
    for row_id, model, *values in cr.fetchall():
        changes = {}
        for column, value in zip(columns, values, strict=True):
            if not value:
                continue
            renamed = rename.expression(value, names=None, strings=model, leaves=model)
            if renamed != value:
                changes[column] = renamed
        if not changes:
            continue
        cr.execute(
            SQL(
                "UPDATE %s SET %s WHERE id = %s",
                SQL.identifier(source.table),
                SQL(", ").join(
                    SQL("%s = %s", SQL.identifier(column), value)
                    for column, value in changes.items()
                ),
                row_id,
            )
        )
        rewritten += 1
    return rewritten


def _rename_in_export_lines(cr: BaseCursor, rename: _FieldRename) -> int:
    # An export template's line is a `/` path read from the template's model.
    if "." in rename.old or not table_exists(cr, "ir_exports_line"):
        return 0
    cr.execute(
        SQL(
            "SELECT line.id, export.resource, line.name FROM ir_exports_line line "
            "JOIN ir_exports export ON export.id = line.export_id "
            "WHERE line.name ~ %s",
            r"(^|/)%s(/|$)" % rename.old,
        )
    )
    rewritten = 0
    for line_id, model, path in cr.fetchall():
        renamed = (
            rename.rename_path(path, model, "/")
            if rename.precise
            else "/".join(
                rename.new if segment == rename.old else segment
                for segment in path.split("/")
            )
        )
        if renamed == path:
            continue
        cr.execute(
            SQL("UPDATE ir_exports_line SET name = %s WHERE id = %s", renamed, line_id)
        )
        rewritten += 1
    return rewritten


CRON_ACTION_SUFFIX = "_ir_actions_server"


def rehome_cron_xmlids(
    cr: _SqlCursor,
    from_module: str,
    to_module: str,
    renamed: Mapping[str, str],
) -> int:
    """Move `ir.cron` xmlids together with their server-action companions.

    Loading a cron from XML registers two xmlids, not one: the cron itself and
    the `ir.actions.server` it delegates to, named `<cron xmlid>_ir_actions_server`.
    A migration that renames or rehomes only the first leaves the second owned by
    a module that no longer declares it, and nothing goes wrong until that module
    is next in `updated_modules`. Then `ir.model.data._process_end()` reads the
    companion as stale and deletes it, which
    `ir_cron_ir_actions_server_id_fkey` refuses because it is `RESTRICT`.

    That failure lands in the stale-data sweep, which runs *after* every module
    has upgraded and committed, so an otherwise complete `-u all` exits non-zero
    with the whole database already migrated. Renaming the pair together is what
    keeps the sweep from ever seeing a half-moved cron.
    """
    pairs = {}
    for old, new in renamed.items():
        pairs[old] = new
        pairs[old + CRON_ACTION_SUFFIX] = new + CRON_ACTION_SUFFIX
    return adopt_xmlids(cr, from_module, to_module, (), pairs)


def repair_orphaned_cron_actions(cr: _SqlCursor) -> int:
    """Re-point companions left behind by a cron rename that moved only the cron.

    Only the companions that still drive a live `ir.cron` are repaired, because
    those are the ones whose deletion the foreign key refuses. The companion is
    re-pointed at the module and name its cron now answers to, never deleted: the
    server action carries the cron's `state`, `code` and `model_id`, so dropping
    it would take the schedule with it.

    A companion that drives no cron is ordinary dead data and is left alone --
    the owning module's own sweep removes it correctly, and a module whose sweep
    can never run is a different defect that has to name its rows deliberately.

    Idempotent, and safe on a database that has nothing to repair.
    """
    cr.execute(
        SQL(
            """
            SELECT stale.id, stale.module, stale.name, cron_data.module, cron_data.name
              FROM ir_model_data stale
              JOIN ir_cron cron ON cron.ir_actions_server_id = stale.res_id
              JOIN ir_model_data cron_data
                ON cron_data.model = 'ir.cron' AND cron_data.res_id = cron.id
             WHERE stale.model = 'ir.actions.server'
               AND stale.name LIKE %s
               AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data owner
                    WHERE owner.model = 'ir.cron'
                      AND owner.module = stale.module
                      AND owner.name = left(stale.name, -%s)
               )
            """,
            f"%{CRON_ACTION_SUFFIX}",
            len(CRON_ACTION_SUFFIX),
        )
    )
    repaired = 0
    for data_id, old_module, old_name, module, cron_name in cr.fetchall():
        name = cron_name + CRON_ACTION_SUFFIX
        cr.execute(
            SQL(
                "UPDATE ir_model_data SET module = %s, name = %s "
                "WHERE id = %s AND NOT EXISTS ("
                "    SELECT 1 FROM ir_model_data taken"
                "     WHERE taken.module = %s AND taken.name = %s AND taken.id != %s"
                ")",
                module,
                name,
                data_id,
                module,
                name,
                data_id,
            )
        )
        _debug.logic(
            "module_data.cron_action_repointed",
            xmlid=f"{old_module}.{old_name}",
            target=f"{module}.{name}",
            applied=bool(cr.rowcount),
        )
        if cr.rowcount:
            repaired += 1
            _logger.info(
                "re-pointed %s.%s to %s.%s, the cron it actually drives",
                old_module,
                old_name,
                module,
                name,
            )
    return repaired


def rename_field(
    cr: BaseCursor,
    model: str,
    old: str,
    new: str,
    *,
    values: Mapping[str, str] | None = None,
) -> None:
    # A stored field renamed in place, not dropped and re-added: the column keeps
    # its data, and the `ir.model.fields` row keeps its id -- which is what every
    # `mail.tracking.value`, export template and access record points at, so a
    # drop-and-add would delete that history with the old row. Its external id
    # and, for a Selection, the value rows and their external ids follow.
    table = _table_of(model)
    column_renamed = column_exists(cr, table, old) and not column_exists(cr, table, new)
    _debug.lifecycle(
        "module_data.rename_field",
        model=model,
        old=old,
        new=new,
        column_renamed=column_renamed,
        values=len(values or {}),
    )
    if column_renamed:
        rename_column(cr, table, old, new)
        if values:
            for old_value, new_value in values.items():
                cr.execute(
                    SQL(
                        "UPDATE %s SET %s = %s WHERE %s = %s",
                        SQL.identifier(table),
                        SQL.identifier(new),
                        new_value,
                        SQL.identifier(new),
                        old_value,
                    )
                )

    cr.execute(
        SQL(
            "SELECT id FROM ir_model_fields WHERE model = %s AND name = %s",
            model,
            old,
        )
    )
    row = cr.fetchone()
    if row is None:
        _debug.logic(
            "module_data.rename_field_skipped", model=model, old=old, reason="no_row"
        )
        return
    field_id = row[0]
    cr.execute(
        SQL(
            "SELECT 1 FROM ir_model_fields WHERE model = %s AND name = %s",
            model,
            new,
        )
    )
    if cr.fetchone():
        _debug.logic(
            "module_data.rename_field_skipped",
            model=model,
            old=old,
            reason="target_exists",
        )
        return
    cr.execute(SQL("UPDATE ir_model_fields SET name = %s WHERE id = %s", new, field_id))
    xmlid_model = model.replace(".", "_")
    cr.execute(
        SQL(
            "UPDATE ir_model_data SET name = %s "
            "WHERE model = 'ir.model.fields' AND name = %s",
            f"field_{xmlid_model}__{new}",
            f"field_{xmlid_model}__{old}",
        )
    )
    if not values:
        return
    for old_value, new_value in values.items():
        cr.execute(
            SQL(
                "UPDATE ir_model_fields_selection SET value = %s "
                "WHERE field_id = %s AND value = %s",
                new_value,
                field_id,
                old_value,
            )
        )
        cr.execute(
            SQL(
                "UPDATE ir_model_data SET name = %s "
                "WHERE model = 'ir.model.fields.selection' AND name = %s",
                f"selection__{xmlid_model}__{new}__{new_value}",
                f"selection__{xmlid_model}__{old}__{old_value}",
            )
        )
    _logger.info("renamed %s.%s to %s", model, old, new)


MODEL_NAME_COLUMNS = (
    "model",
    "model_id",
    "res_model",
    "model_name",
    "src_model",
    "parent_res_model",
    "relation",
    "res_model_name",
    "alias_model",
    "resource",
)
_MODEL_EXPRESSION_COLUMNS = (
    ("ir_act_window", ("domain", "context")),
    ("ir_act_server", ("code",)),
    ("ir_filters", ("domain", "context", "sort")),
    ("ir_ui_view", ("arch_db",)),
    ("ir_embedded_actions", ("domain", "context")),
)


def rename_model(cr: BaseCursor, old: str, new: str) -> dict[str, str]:
    # Exact names only, never LIKE '%old%': `crm_team` is a prefix of
    # `crm_team_member`, and a substring rewrite renames both.
    old_table, new_table = old.replace(".", "_"), new.replace(".", "_")
    relations = _rename_model_relations(cr, old, old_table, new_table)
    _rename_table_with_dependents(cr, old_table, new_table)
    _rewrite_model_registry(cr, old, new, old_table, new_table)
    _repoint_model_name_columns(cr, old, new)
    _rewrite_reference_values(cr, old, new)
    rewrite_quoted_model_names(cr, old, new)
    _debug.lifecycle(
        "module_data.rename_model", old=old, new=new, relations=len(relations)
    )
    _logger.info(
        "renamed model %s to %s, with %d join table(s)%s",
        old,
        new,
        len(relations),
        "".join(f", {a} -> {b}" for a, b in relations.items()),
    )
    return relations


def _rename_table_with_dependents(cr: BaseCursor, old: str, new: str) -> bool:
    if not table_exists(cr, old) or table_exists(cr, new):
        return False
    cr.execute(
        SQL("ALTER TABLE %s RENAME TO %s", SQL.identifier(old), SQL.identifier(new))
    )
    cr.execute(
        SQL(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = %s::regclass AND conname LIKE %s",
            new,
            old.replace("_", "\\_") + "\\_%",
        )
    )
    for (name,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER TABLE %s RENAME CONSTRAINT %s TO %s",
                SQL.identifier(new),
                SQL.identifier(name),
                SQL.identifier(new + name[len(old) :]),
            )
        )
    cr.execute(
        SQL(
            "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() "
            "AND tablename = %s AND indexname LIKE %s",
            new,
            old.replace("_", "\\_") + "\\_%",
        )
    )
    for (name,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER INDEX %s RENAME TO %s",
                SQL.identifier(name),
                SQL.identifier(new + name[len(old) :]),
            )
        )
    cr.execute(
        SQL(
            "SELECT 1 FROM pg_sequences WHERE schemaname = current_schema() "
            "AND sequencename = %s",
            old + "_id_seq",
        )
    )
    if cr.fetchone():
        cr.execute(
            SQL(
                "ALTER SEQUENCE %s RENAME TO %s",
                SQL.identifier(old + "_id_seq"),
                SQL.identifier(new + "_id_seq"),
            )
        )
    return True


def _rename_model_relations(
    cr: BaseCursor, old: str, old_table: str, new_table: str
) -> dict[str, str]:
    cr.execute(
        SQL(
            "SELECT DISTINCT model, relation, relation_table, column1, column2 "
            "FROM ir_model_fields WHERE ttype = 'many2many' "
            "AND relation_table IS NOT NULL AND (model = %s OR relation = %s)",
            old,
            old,
        )
    )
    old_column, new_column = f"{old_table}_id", f"{new_table}_id"
    renamed: dict[str, str] = {}
    for model, relation, relation_table, column1, column2 in cr.fetchall():
        tables = [model.replace(".", "_"), relation.replace(".", "_")]
        target = relation_table
        if relation_table == "_".join(sorted(tables)) + "_rel":
            moved = [new_table if t == old_table else t for t in tables]
            target = "_".join(sorted(moved)) + "_rel"
        if target != relation_table and table_exists(cr, relation_table):
            if table_exists(cr, target):
                raise ValueError(
                    f"both {relation_table} and {target} exist; refusing to guess "
                    "which one holds the links"
                )
            _rename_table_with_dependents(cr, relation_table, target)
            renamed[relation_table] = target
        if table_exists(cr, target):
            for column in (column1, column2):
                if column == old_column and not column_exists(cr, target, new_column):
                    rename_column(cr, target, old_column, new_column)
        cr.execute(
            SQL(
                "UPDATE ir_model_fields SET relation_table = %s, "
                "column1 = CASE WHEN column1 = %s THEN %s ELSE column1 END, "
                "column2 = CASE WHEN column2 = %s THEN %s ELSE column2 END "
                "WHERE ttype = 'many2many' AND relation_table = %s",
                target,
                old_column,
                new_column,
                old_column,
                new_column,
                relation_table,
            )
        )
        if target != relation_table:
            cr.execute(
                SQL(
                    "UPDATE ir_model_relation SET name = %s WHERE name = %s",
                    target,
                    relation_table,
                )
            )
    return renamed


def _rewrite_model_registry(
    cr: BaseCursor, old: str, new: str, old_table: str, new_table: str
) -> None:
    for statement in (
        "UPDATE ir_model SET model = %s WHERE model = %s",
        "UPDATE ir_model_fields SET model = %s WHERE model = %s",
        "UPDATE ir_model_fields SET relation = %s WHERE relation = %s",
    ):
        cr.execute(SQL(statement, new, old))
    owned = SQL("(SELECT id FROM ir_model WHERE model = %s)", new)
    cr.execute(
        SQL(
            "UPDATE ir_model_constraint SET name = %s || substring(name from %s) "
            "WHERE model = %s AND name LIKE %s",
            new_table + "_",
            len(old_table) + 2,
            owned,
            old_table.replace("_", "\\_") + "\\_%",
        )
    )
    cr.execute(
        SQL(
            "UPDATE ir_model_data SET name = %s WHERE model = 'ir.model' AND name = %s",
            f"model_{new_table}",
            f"model_{old_table}",
        )
    )
    for prefix, xmlid_model, source, scope in (
        ("field_{}__", "ir.model.fields", "ir_model_fields", "model_id"),
        ("selection__{}__", "ir.model.fields.selection", None, None),
        ("model_inherit__{}__", "ir.model.inherit", "ir_model_inherit", "model_id"),
        ("constraint_{}_", "ir.model.constraint", "ir_model_constraint", "model"),
    ):
        old_prefix, new_prefix = prefix.format(old_table), prefix.format(new_table)
        restrict = (
            SQL(
                " AND res_id IN (SELECT id FROM %s WHERE %s = %s)",
                SQL.identifier(source),
                SQL.identifier(scope),
                owned,
            )
            if source and scope
            else SQL()
        )
        cr.execute(
            SQL(
                "UPDATE ir_model_data SET name = %s || substring(name from %s) "
                "WHERE model = %s AND name LIKE %s%s",
                new_prefix,
                len(old_prefix) + 1,
                xmlid_model,
                old_prefix.replace("_", "\\_") + "%",
                restrict,
            )
        )


def _repoint_model_name_columns(cr: BaseCursor, old: str, new: str) -> None:
    cr.execute(
        SQL(
            "SELECT c.table_name, c.column_name FROM information_schema.columns c "
            "JOIN information_schema.tables t ON t.table_schema = c.table_schema "
            "AND t.table_name = c.table_name "
            "WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE' "
            "AND c.data_type IN ('character varying', 'text') "
            "AND c.column_name = ANY(%s)",
            list(MODEL_NAME_COLUMNS),
        )
    )
    for table, column in cr.fetchall():
        cr.execute(
            SQL(
                "UPDATE %s SET %s = %s WHERE %s = %s",
                SQL.identifier(table),
                SQL.identifier(column),
                new,
                SQL.identifier(column),
                old,
            )
        )


def _rewrite_reference_values(cr: BaseCursor, old: str, new: str) -> None:
    cr.execute(
        "SELECT model, name FROM ir_model_fields WHERE ttype = 'reference' AND store"
    )
    for model, field in cr.fetchall():
        table = _table_of(model)
        if not column_exists(cr, table, field):
            continue
        cr.execute(
            SQL(
                "UPDATE %s SET %s = %s || substring(%s from %s) WHERE %s LIKE %s",
                SQL.identifier(table),
                SQL.identifier(field),
                new + ",",
                SQL.identifier(field),
                len(old) + 2,
                SQL.identifier(field),
                old.replace("_", "\\_") + ",%",
            )
        )


def rewrite_quoted_model_names(cr: BaseCursor, old: str, new: str) -> None:
    existing = set(get_tables_existing(cr, [t for t, _ in _MODEL_EXPRESSION_COLUMNS]))
    for table, columns in _MODEL_EXPRESSION_COLUMNS:
        if table not in existing:
            continue
        types = get_table_columns(cr, table)
        for column in columns:
            if column not in types:
                continue
            for quote in ("'", '"'):
                needle, replacement = f"{quote}{old}{quote}", f"{quote}{new}{quote}"
                if types[column]["udt_name"] == "jsonb":
                    # jsonb::text escapes a double quote, so each value is
                    # rewritten as the text it is, not as the document's text
                    cr.execute(
                        SQL(
                            """
                            UPDATE %(table)s SET %(column)s = (
                                   SELECT jsonb_object_agg(key, replace(value, %(needle)s, %(new)s))
                                     FROM jsonb_each_text(%(column)s))
                             WHERE EXISTS (
                                   SELECT 1 FROM jsonb_each_text(%(column)s)
                                    WHERE position(%(needle)s in value) > 0)
                            """,
                            table=SQL.identifier(table),
                            column=SQL.identifier(column),
                            needle=needle,
                            new=replacement,
                        )
                    )
                    continue
                cr.execute(
                    SQL(
                        "UPDATE %s SET %s = replace(%s, %s, %s) "
                        "WHERE position(%s in %s) > 0",
                        SQL.identifier(table),
                        SQL.identifier(column),
                        SQL.identifier(column),
                        needle,
                        replacement,
                        needle,
                        SQL.identifier(column),
                    )
                )
