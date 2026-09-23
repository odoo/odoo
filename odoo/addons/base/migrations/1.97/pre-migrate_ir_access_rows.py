"""Every access line and record rule of the database becomes ir.access rows.

Until now the decision read the real ir.access rows plus the rows
`ir_access_convert.synthesize()` made of `ir_model_access` and `ir_rule` at
load. The modules' data files are converted to `security/ir.access.csv`, and
their rows reuse the external ids of the lines and rules they come from, so
this runs before any module loads (base is loaded first): it converts every
line and rule the database holds with the same `convert()` the data files were
converted with, moves each external id onto the row it names, keeping its
noupdate flag, and empties the two tables. The modules' files then update the
rows they ship and `_process_end` drops the converted rows no file names, as
it dropped the old records; a noupdate row stays as the database had it (an
administrator's edit, a rule a module no longer ships), which is what the old
engine applied. One exception: where the module's file ships the same external
id as another kind of row or for another group (a noupdate rule whose group
link was lost reads as a global rule), the rows the file derives beside it do
not fit the database's row, so that row is left for the file to update.

A line or rule an administrator switched off becomes a switched-off row on its
own, not paired with anything: switching it on again is a decision about the
new model.

The census logged at the end accounts for every source: turned into rows
(or covered by a row of wider reach), switched off, a rule no access line gives
its group (which never had an effect), or a rule paired only with lines of
modules it does not load with (the data files' conversion drops those pairs,
and a module that auto-installs with both ships the row where one exists);
`lost` must read 0.
"""

import csv
import logging
import os
from collections import Counter

from lxml import etree

from odoo.modules.module import get_module_path

from odoo.addons.base.models.ir_access_convert import (
    GROUP_EVERYONE,
    PERM_OF_OPERATION,
    convert,
    normalize_domain,
    operation_string,
    read_database,
)

_logger = logging.getLogger(__name__)


def _group_ids(cr) -> dict[str, int]:
    cr.execute(
        "SELECT module || '.' || name, res_id FROM ir_model_data "
        "WHERE model = 'res.groups'"
    )
    return dict(cr.fetchall())


def _model_ids(cr) -> dict[str, int]:
    cr.execute("SELECT model, id FROM ir_model")
    return dict(cr.fetchall())


def _inactive_rows(acl_lines, rules, implications, module_deps) -> list[dict]:
    # the switched-off lines and rules convert among themselves, as they would
    # act if switched on together (project sharing switches a line and a rule
    # on at once); a rule left without a line to pair with stands alone
    lines = [{**line, "active": True} for line in acl_lines if not line["active"]]
    off_rules = [{**rule, "active": True} for rule in rules if not rule["active"]]
    rows, report = convert(lines, off_rules, implications, module_deps=module_deps)
    for rule in off_rules:
        key = rule["xmlid"] or f"ir.rule#{rule['id']}"
        if key in report.source_map or key in report.bound_nobody:
            continue
        ops = operation_string(
            op
            for op, perm in PERM_OF_OPERATION.items()
            if rule.get(perm) is None or rule.get(perm)
        )
        for index, group in enumerate(rule["groups"] or [None]):
            xmlid = rule["xmlid"]
            if xmlid and index:
                xmlid = f"{xmlid}_{group.rpartition('.')[2]}"
            rows.append(
                {
                    "xmlid": xmlid,
                    "name": rule["name"] or rule["model"],
                    "model": rule["model"],
                    "kind": "permission" if group else "guard",
                    "guard_scope": None if group else "everyone",
                    "group": group or GROUP_EVERYONE,
                    "operation": ops or "crud",
                    "domain": normalize_domain(rule["domain_force"]),
                    "sources": [key],
                    "noupdate": rule["noupdate"],
                    "deactivated_by": [],
                }
            )
    for row in rows:
        row["active"] = False
    return rows


class _ShippedRows:
    # the (kind, group) of the rows a module's security files ship, read from
    # disk on demand
    def __init__(self, modules):
        self.modules = set(modules)
        self.cache: dict[str, dict[str, tuple[str, str]]] = {}

    def row(self, module: str, name: str) -> tuple[str, str] | None:
        if module not in self.modules:
            return None
        if module not in self.cache:
            self.cache[module] = self._read(module)
        return self.cache[module].get(name)

    def _read(self, module: str) -> dict[str, tuple[str, str]]:
        rows: dict[str, tuple[str, str]] = {}
        path = get_module_path(module)
        if not path:
            return rows

        def qualify(ref: str) -> str:
            return ref if "." in ref else f"{module}.{ref}"

        csv_path = os.path.join(path, "security", "ir.access.csv")
        if os.path.isfile(csv_path):
            with open(csv_path, newline="", encoding="utf-8") as stream:
                for line in csv.DictReader(stream):
                    rows[line["id"]] = (line["kind"], qualify(line["group_id/id"]))
        xml_path = os.path.join(path, "security", "ir_access.xml")
        if os.path.isfile(xml_path):
            for record in etree.parse(xml_path).iter("record"):
                fields = {f.get("name"): f for f in record.iter("field")}
                if (
                    "kind" in fields
                    and "group_id" in fields
                    and "." not in record.get("id")
                ):
                    rows[record.get("id")] = (
                        fields["kind"].text,
                        qualify(fields["group_id"].get("ref")),
                    )
        return rows


def _ensure_ir_access_table(cr) -> None:
    # a database older than the ir.access model has no table yet: a pre-migrate
    # runs before base's schema update, so create what this script writes, with
    # the column types the ORM gives these fields, and let base's update add
    # the rest (constraints, foreign keys, the other columns)
    cr.execute("SELECT to_regclass('public.ir_access')")
    if cr.fetchone()[0] is not None:
        return
    cr.execute(
        """
        CREATE TABLE ir_access (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            active BOOLEAN,
            model_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            kind VARCHAR NOT NULL,
            guard_scope VARCHAR,
            operation VARCHAR NOT NULL,
            domain VARCHAR,
            for_read BOOLEAN,
            for_write BOOLEAN,
            for_create BOOLEAN,
            for_unlink BOOLEAN,
            create_uid INTEGER,
            write_uid INTEGER,
            create_date TIMESTAMP,
            write_date TIMESTAMP
        )
        """
    )
    _logger.info("ir.access conversion: created the ir_access table")


def _ensure_group_everyone(cr) -> None:
    # every guard and every group-less access line converts to base.group_everyone,
    # which a database older than the ir.access model does not have yet; create
    # it as base_groups.xml declares it, implied by the three user types, and let
    # base's data load update it
    cr.execute(
        "SELECT 1 FROM ir_model_data WHERE module = 'base' AND name = 'group_everyone'"
    )
    if cr.fetchone():
        return
    cr.execute(
        """
        INSERT INTO res_groups (name, comment, create_uid, write_uid, create_date,
                                write_date)
        VALUES ('{"en_US": "Role / Everyone"}'::jsonb,
                '{"en_US": "Every user, internal, portal or public: an access given to it is given to all."}'::jsonb,
                1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC')
        RETURNING id
        """
    )
    [everyone] = cr.fetchone()
    cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        VALUES ('base', 'group_everyone', 'res.groups', %s, false)
        """,
        [everyone],
    )
    cr.execute(
        """
        INSERT INTO res_groups_implied_rel (gid, hid)
        SELECT res_id, %s FROM ir_model_data
         WHERE module = 'base'
           AND name IN ('group_user', 'group_portal', 'group_public')
        """,
        [everyone],
    )
    _logger.info("ir.access conversion: created base.group_everyone")


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT count(*) FROM ir_model_access")
    [acl_count] = cr.fetchone()
    cr.execute("SELECT count(*) FROM ir_rule")
    [rule_count] = cr.fetchone()
    if not (acl_count or rule_count):
        return
    _ensure_ir_access_table(cr)
    _ensure_group_everyone(cr)
    acl_lines, rules, implications, module_deps = read_database(cr)
    rows, report = convert(acl_lines, rules, implications, module_deps=module_deps)
    for row in rows:
        row["active"] = not set(row["deactivated_by"]) & set(module_deps)
    rows += _inactive_rows(acl_lines, rules, implications, module_deps)

    groups = _group_ids(cr)
    models = _model_ids(cr)
    cr.execute(
        "SELECT module || '.' || name FROM ir_model_data WHERE model = 'ir.access'"
    )
    taken = {xmlid for [xmlid] in cr.fetchall()}

    def group_id(key: str) -> int:
        if key.startswith("res.groups#"):
            return int(key.partition("#")[2])
        return groups[key]

    cr.execute(
        "DELETE FROM ir_model_data WHERE model IN ('ir.model.access', 'ir.rule')"
    )
    created = Counter()
    files = _ShippedRows(module_deps)
    reshaped: list[str] = []
    for row in rows:
        ops = row["operation"]
        cr.execute(
            """
            INSERT INTO ir_access (
                name, active, model_id, group_id, kind, guard_scope, operation,
                domain, for_read, for_write, for_create, for_unlink,
                create_uid, write_uid, create_date, write_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 1,
                    now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC')
            RETURNING id
            """,
            [
                row["name"],
                row["active"],
                models[row["model"]],
                group_id(row["group"]),
                row["kind"],
                row["guard_scope"] or "everyone",
                ops,
                row["domain"] or None,
                "r" in ops,
                "u" in ops,
                "c" in ops,
                "d" in ops,
            ],
        )
        [row["id"]] = cr.fetchone()
        created[row["kind"], row["active"]] += 1
        xmlid = row["xmlid"]
        if not xmlid or "." not in xmlid:
            continue
        if xmlid in taken:
            _logger.warning(
                "ir.access %s already exists; row %s keeps no external id",
                xmlid,
                row["id"],
            )
            continue
        taken.add(xmlid)
        module, _dot, name = xmlid.partition(".")
        noupdate = bool(row["noupdate"])
        if noupdate and (shipped := files.row(module, name)) is not None:
            if shipped != (row["kind"], row["group"]):
                noupdate = False
                reshaped.append(xmlid)
        cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            VALUES (%s, %s, 'ir.access', %s, %s)
            """,
            [module, name, row["id"], noupdate],
        )
    if reshaped:
        _logger.info(
            "ir.access conversion: %s noupdate rows left for their module's file, "
            "which ships them as another kind or for another group: %s",
            len(reshaped),
            ", ".join(sorted(reshaped)),
        )
    cr.execute("DELETE FROM rule_group_rel")
    cr.execute("DELETE FROM ir_rule")
    cr.execute("DELETE FROM ir_model_access")

    census = Counter()
    represented = set(report.source_map) | {
        source for row in rows if not row["active"] for source in row["sources"]
    }
    dead = {entry["rule"] for entry in report.dead_rules if entry["whole"]}
    unplaced = {entry["rule"] for entry in report.unplaced}
    bound_nobody = {
        rule["xmlid"] or f"ir.rule#{rule['id']}"
        for rule in rules
        if not rule["groups"] and rule["global"] is False
    }
    for key in sorted(bound_nobody):
        _logger.warning(
            "ir.access conversion: rule %s has no group and is not global, so it "
            "bound nobody; it is dropped",
            key,
        )
    for kind, sources in (("ir.model.access", acl_lines), ("ir.rule", rules)):
        for source in sources:
            key = source["xmlid"] or f"{kind}#{source['id']}"
            origin = (
                "module"
                if source["xmlid"] and source["xmlid"].partition(".")[0] in module_deps
                else "custom"
            )
            if key in bound_nobody:
                state = "rule with no group that is not global: bound nobody"
            elif not source["active"]:
                state = "switched off, kept switched off"
            elif key in represented:
                state = "turned into rows"
            elif key in report.redundant:
                state = "rule over a line it never narrowed: the group reaches all"
            elif key in unplaced:
                state = "rule paired only with lines of modules it does not load with"
            elif key in dead:
                state = "rule no access line gives its group, never had an effect"
            else:
                state = "lost"
            census[kind, origin, state] += 1
    lost = sum(count for (_k, _o, state), count in census.items() if state == "lost")
    _logger.info(
        "ir.access conversion: %s access lines and %s rules -> %s rows (%s)",
        acl_count,
        rule_count,
        len(rows),
        ", ".join(
            f"{kind}{'' if active else ' switched off'}: {count}"
            for (kind, active), count in sorted(created.items())
        ),
    )
    for (kind, origin, state), count in sorted(census.items()):
        _logger.info(
            "ir.access conversion census: %s %s %s: %s", origin, kind, state, count
        )
    for entry in report.unplaced:
        _logger.info(
            "ir.access conversion: %s and %s come from modules that do not load "
            "each other, so they make no row, as in the data files (a module "
            "that auto-installs with both ships it)",
            entry["acl"],
            entry["rule"],
        )
    if lost:
        _logger.error("ir.access conversion: %s sources lost", lost)
    else:
        _logger.info("ir.access conversion: 0 sources lost")
