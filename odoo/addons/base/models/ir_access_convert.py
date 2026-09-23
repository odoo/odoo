import itertools
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

GROUP_EVERYONE = "base.group_everyone"
EXCLUSIVE_GROUPS = frozenset(
    {"base.group_user", "base.group_portal", "base.group_public"}
)
OPERATIONS = "crud"
PERM_OF_OPERATION = {
    "c": "perm_create",
    "r": "perm_read",
    "u": "perm_write",
    "d": "perm_unlink",
}
TRUE = ""
# a line that grants nothing keeps its place, and its model keeps a row
NOTHING = "[(0, '=', 1)]"
_TRUE_DOMAIN_RE = re.compile(
    r"""^\s*(\[\s*\]|\[\s*\(\s*1\s*,\s*(["'])=\2\s*,\s*1\s*\)\s*\])\s*$"""
)
_GROUP_TEST_RE = re.compile(r"\b(all_group_ids|group_ids|groups_id|has_group)\b")


@dataclass(frozen=True, slots=True)
class Effective:
    guards: frozenset[str]
    grants: frozenset[str] | None

    @property
    def sees_all(self) -> bool:
        return self.grants is not None and TRUE in self.grants

    @classmethod
    def of(cls, guards: Iterable[str], grants: Iterable[str] | None) -> Effective:
        guards = frozenset(guards) - {TRUE}
        if grants is None:
            return cls(frozenset(), None)
        grants = frozenset(grants)
        return cls(guards, frozenset({TRUE}) if TRUE in grants else grants)

    def render(self) -> str:
        if self.grants is None:
            return "no access"
        grants = "all" if self.sees_all else " | ".join(map(_flat, sorted(self.grants)))
        if not self.guards:
            return grants
        return f"{grants} & guards({' & '.join(map(_flat, sorted(self.guards)))})"


def _flat(domain: str) -> str:
    return " ".join(domain.split())


@dataclass(slots=True)
class ConversionReport:
    xmlid_map: dict[str, list[str]] = field(default_factory=dict)
    source_map: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    monotonicity: list[dict[str, Any]] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)
    see_all_beside_rules: list[dict[str, Any]] = field(default_factory=list)
    dead_rules: list[dict[str, Any]] = field(default_factory=list)
    mode_blind_rules: list[str] = field(default_factory=list)
    group_test_domains: list[str] = field(default_factory=list)
    unmapped: list[dict[str, Any]] = field(default_factory=list)
    unplaced: list[dict[str, Any]] = field(default_factory=list)
    redundant: set[str] = field(default_factory=set)
    bound_nobody: list[str] = field(default_factory=list)
    collisions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _Acl:
    key: str
    xmlid: str | None
    module: str | None
    name: str
    model: str
    group: str
    ops: frozenset[str]
    noupdate: bool = False


@dataclass(slots=True)
class _Rule:
    key: str
    xmlid: str | None
    module: str | None
    name: str
    model: str
    group: str | None
    groups: tuple[str, ...]
    ops: frozenset[str]
    domain: str
    restrict: bool
    noupdate: bool = False


def normalize_domain(domain: str | None) -> str:
    if not domain or _TRUE_DOMAIN_RE.match(domain):
        return TRUE
    return domain.strip()


def operation_string(ops: Iterable[str]) -> str:
    ops = set(ops)
    return "".join(op for op in OPERATIONS if op in ops)


def group_closures(
    group_implications: Mapping[str, Iterable[str]],
    extra: Iterable[str] = (),
) -> dict[str, frozenset[str]]:
    implied = {group: set(targets) for group, targets in group_implications.items()}
    universe = set(implied) | {g for gs in implied.values() for g in gs} | set(extra)
    universe.add(GROUP_EVERYONE)
    closures: dict[str, frozenset[str]] = {}
    for group in universe:
        seen = {group, GROUP_EVERYONE}
        todo = [group]
        while todo:
            for target in implied.get(todo.pop(), ()):
                if target not in seen:
                    seen.add(target)
                    todo.append(target)
        closures[group] = frozenset(seen)
    return closures


def _local_name(xmlid: str) -> str:
    return xmlid.rpartition(".")[2]


def _module_of(xmlid: str | None) -> str | None:
    return xmlid.partition(".")[0] if xmlid and "." in xmlid else None


class _Converter:
    def __init__(
        self,
        acl_lines: Sequence[Mapping[str, Any]],
        rules: Sequence[Mapping[str, Any]],
        group_implications: Mapping[str, Iterable[str]],
        module_deps: Mapping[str, Iterable[str]] | None,
    ):
        self.report = ConversionReport()
        self._absorbed: list[dict[str, Any]] = []
        self.module_deps = (
            {module: set(deps) for module, deps in module_deps.items()}
            if module_deps is not None
            else None
        )
        self.acls: dict[str, list[_Acl]] = defaultdict(list)
        self.rules: dict[str, list[_Rule]] = defaultdict(list)
        mentioned: set[str] = set()
        for index, line in enumerate(acl_lines):
            if acl := self._read_acl(index, line):
                self.acls[acl.model].append(acl)
                mentioned.add(acl.group)
        for index, rule in enumerate(rules):
            for parsed in self._read_rule(index, rule):
                self.rules[parsed.model].append(parsed)
                if parsed.group:
                    mentioned.add(parsed.group)
        self.closure = group_closures(group_implications, mentioned)

    def _unmapped(self, key: str, reason: str) -> None:
        self.report.unmapped.append({"source": key, "reason": reason})

    def _module(self, line: Mapping[str, Any]) -> str | None:
        # a source belongs to a module only when that module is known to be
        # loaded: an exported or hand-made record is always present
        module = line.get("module") or _module_of(line.get("xmlid"))
        if self.module_deps is not None and module not in self.module_deps:
            return None
        return module

    def _read_acl(self, index: int, line: Mapping[str, Any]) -> _Acl | None:
        key = line.get("xmlid") or f"ir.model.access#{line.get('id', index)}"
        if not line.get("active", True):
            self._unmapped(key, "inactive access line, not converted")
            return None
        if not line.get("model"):
            self._unmapped(key, "access line names no model")
            return None
        ops = frozenset(op for op, perm in PERM_OF_OPERATION.items() if line.get(perm))
        return _Acl(
            key=key,
            xmlid=line.get("xmlid"),
            module=self._module(line),
            name=line.get("name") or line["model"],
            model=line["model"],
            group=line.get("group") or GROUP_EVERYONE,
            ops=ops,
            noupdate=bool(line.get("noupdate")),
        )

    def _read_rule(self, index: int, rule: Mapping[str, Any]) -> list[_Rule]:
        key = rule.get("xmlid") or f"ir.rule#{rule.get('id', index)}"
        if not rule.get("active", True):
            self._unmapped(key, "inactive rule, not converted")
            return []
        if not rule.get("model"):
            self._unmapped(key, "rule names no model")
            return []
        declared = [rule.get(perm) for perm in PERM_OF_OPERATION.values()]
        if all(value is None for value in declared):
            self.report.mode_blind_rules.append(key)
        ops = frozenset(
            op
            for op, perm in PERM_OF_OPERATION.items()
            if rule.get(perm) is None or rule.get(perm)
        )
        if not ops:
            self._unmapped(key, "rule applies to no operation")
            return []
        composition = rule.get("composition") or "grant"
        if composition not in ("grant", "restrict"):
            self._unmapped(key, f"unknown composition {composition!r}")
            return []
        domain = normalize_domain(rule.get("domain_force"))
        if _GROUP_TEST_RE.search(domain):
            self.report.group_test_domains.append(key)
        groups = tuple(sorted(set(rule.get("groups") or ())))
        if not groups and rule.get("global") is False:
            # a rule whose groups were all deleted keeps global False, and a
            # rule was selected by global OR one of the user's groups: it bound
            # nobody
            self.report.bound_nobody.append(key)
            self._unmapped(key, "rule with no group that is not global binds nobody")
            return []
        common = {
            "key": key,
            "xmlid": rule.get("xmlid"),
            "module": self._module(rule),
            "name": rule.get("name") or rule["model"],
            "model": rule["model"],
            "groups": groups,
            "ops": ops,
            "domain": domain,
            "restrict": composition == "restrict",
            "noupdate": bool(rule.get("noupdate")),
        }
        if not groups:
            return [_Rule(group=None, **common)]
        return [_Rule(group=group, **common) for group in groups]

    def _loaded_with(self, module: str | None, other: str | None) -> bool:
        # whether `other`'s records are loaded whenever `module`'s are
        if self.module_deps is None or module is None or other is None:
            return True
        return other in self.module_deps.get(module, ())

    def _owner(self, acl: _Acl, rule: _Rule) -> tuple[bool, str | None]:
        if self.module_deps is None:
            return True, rule.module
        if acl.module is None or rule.module is None:
            return True, None
        if self._loaded_with(acl.module, rule.module):
            return True, acl.module
        if self._loaded_with(rule.module, acl.module):
            return True, rule.module
        return False, None

    def convert(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for model in sorted(set(self.acls) | set(self.rules)):
            rows.extend(self._convert_model(model))
        self._name_rows(rows)
        self._audit(rows)
        return rows

    def _row(self, kind, model, group, ops, domain, name, sources, **extra):
        return {
            "kind": kind,
            "model": model,
            "group": group,
            "ops": set(ops),
            "domain": domain,
            "name": name,
            "sources": list(sources),
            "guard_scope": None,
            "conditional": (),
            **extra,
        }

    def _convert_model(self, model: str) -> list[dict[str, Any]]:
        acls = self.acls.get(model, [])
        rules = self.rules.get(model, [])
        grants = [rule for rule in rules if rule.group and not rule.restrict]
        rows: list[dict[str, Any]] = []
        produced: dict[tuple[str, str], set[str]] = defaultdict(set)
        for acl in acls:
            if not acl.ops:
                rows.append(
                    self._row(
                        "permission",
                        model,
                        acl.group,
                        "r",
                        NOTHING,
                        acl.name,
                        [acl.key],
                        module=acl.module,
                        base_xmlid=acl.xmlid,
                        from_rule=None,
                        noupdate=acl.noupdate,
                    )
                )
                continue
            closure = self.closure[acl.group]
            restricting = [rule for rule in grants if rule.group in closure]
            # an operation is restricted where a rule of the group's closure
            # governs it; a rule of a module the line's module does not load
            # restricts it only where that module is installed, so the line
            # keeps that operation in a row the rule's module deactivates
            always: set[str] = set()
            modules_of: dict[str, set[str | None]] = defaultdict(set)
            for rule in restricting:
                for op in rule.ops & acl.ops:
                    if self._loaded_with(acl.module, rule.module):
                        always.add(op)
                    else:
                        modules_of[op].add(rule.module)
            conditional: dict[tuple[str, ...], set[str]] = defaultdict(set)
            for op, modules in modules_of.items():
                if op not in always:
                    conditional[tuple(sorted(modules))].add(op)
            unrestricted = set(acl.ops) - always - set(modules_of)
            for modules, ops in [((), unrestricted), *sorted(conditional.items())]:
                if not ops:
                    continue
                rows.append(
                    self._row(
                        "permission",
                        model,
                        acl.group,
                        ops,
                        TRUE,
                        acl.name,
                        [acl.key],
                        module=acl.module,
                        base_xmlid=acl.xmlid,
                        from_rule=None,
                        conditional=modules,
                        noupdate=acl.noupdate,
                    )
                )
            if unrestricted:
                beside = sorted(
                    {rule.group for rule in grants if rule.ops & unrestricted} - closure
                )
                if beside:
                    self.report.see_all_beside_rules.append(
                        {
                            "acl": acl.key,
                            "model": model,
                            "group": acl.group,
                            "operation": operation_string(unrestricted),
                            "rule_groups": beside,
                        }
                    )
            for rule in grants:
                if rule.group in closure:
                    group = acl.group
                elif acl.group in self.closure[rule.group]:
                    group = rule.group
                else:
                    continue
                ops = (rule.ops & acl.ops) - unrestricted
                if not ops:
                    produced[rule.key, rule.group].update(rule.ops & acl.ops)
                    self.report.redundant.add(rule.key)
                    continue
                placed, owner = self._owner(acl, rule)
                if not placed:
                    self.report.unplaced.append(
                        {
                            "acl": acl.key,
                            "rule": rule.key,
                            "model": model,
                            "group": group,
                            "operation": operation_string(ops),
                        }
                    )
                    continue
                produced[rule.key, rule.group].update(rule.ops & acl.ops)
                rows.append(
                    self._row(
                        "permission",
                        model,
                        group,
                        ops,
                        rule.domain,
                        rule.name,
                        [acl.key, rule.key],
                        module=owner,
                        base_xmlid=rule.xmlid,
                        from_rule=rule.key,
                        primary=rule.groups == (group,),
                        noupdate=rule.noupdate,
                    )
                )
        for rule in rules:
            if not rule.group or rule.restrict:
                rows.append(
                    self._row(
                        "guard",
                        model,
                        rule.group or GROUP_EVERYONE,
                        rule.ops,
                        rule.domain,
                        rule.name,
                        [rule.key],
                        module=rule.module,
                        base_xmlid=rule.xmlid,
                        from_rule=rule.key,
                        guard_scope="members" if rule.group else "everyone",
                        primary=len(rule.groups) <= 1,
                        noupdate=rule.noupdate,
                    )
                )
                continue
            if dead := rule.ops - produced[rule.key, rule.group]:
                self.report.dead_rules.append(
                    {
                        "rule": rule.key,
                        "model": model,
                        "group": rule.group,
                        "operation": operation_string(dead),
                        "domain": rule.domain,
                        "whole": dead == rule.ops,
                    }
                )
        return self._simplify(rows)

    def _simplify(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[tuple, dict[str, Any]] = {}
        for row in rows:
            key = (
                row["kind"],
                row["guard_scope"],
                row["group"],
                row["domain"],
                row["module"],
                row["from_rule"],
                row["conditional"],
            )
            if (kept := merged.get(key)) is None:
                merged[key] = row
                continue
            kept["ops"] |= row["ops"]
            kept["noupdate"] = kept["noupdate"] or row["noupdate"]
            kept["sources"].extend(
                s for s in row["sources"] if s not in kept["sources"]
            )
        rows = list(merged.values())
        # a row deactivated where another module is installed neither absorbs
        # nor is absorbed: it is not there in every install the other row is
        see_all = [
            (index, row, frozenset(row["ops"]))
            for index, row in enumerate(rows)
            if row["kind"] == "permission"
            and row["domain"] == TRUE
            and not row["conditional"]
        ]
        kept_rows = []
        for index, row in enumerate(rows):
            if row["kind"] == "permission" and not row["conditional"]:
                for other_index, other, other_ops in see_all:
                    if other_index == index or not self._absorbs(other, row):
                        continue
                    mutual = row["domain"] == TRUE and self._absorbs(row, other)
                    if mutual and other_index > index:
                        continue
                    if covered := row["ops"] & other_ops:
                        row["ops"] -= covered
                        row.setdefault("absorbed_by", []).append(other)
                if not row["ops"]:
                    self._absorbed.append(row)
                    continue
            kept_rows.append(row)
        return kept_rows

    def _absorbs(self, see_all: dict[str, Any], row: dict[str, Any]) -> bool:
        if see_all["group"] not in self.closure[row["group"]]:
            return False
        if see_all["module"] == row["module"]:
            return True
        if self.module_deps is None or see_all["module"] is None:
            return False
        return see_all["module"] in self.module_deps.get(row["module"] or "", ())

    def _name_rows(self, rows: list[dict[str, Any]]) -> None:
        # a row's external id depends on its own sources only, never on which
        # other rows exist: the database's conversion and the data files'
        # name the same row alike
        for row in rows:
            base = row["base_xmlid"]
            if base is None:
                row["xmlid"] = None
                continue
            name = _local_name(base)
            if row["from_rule"] is None:
                if row["conditional"]:
                    name = f"{name}_{operation_string(row['ops'])}"
            elif not row.get("primary", True):
                name = f"{name}_{_local_name(row['group'])}"
            module = row["module"] or _module_of(base)
            row["xmlid"] = f"{module}.{name}" if module else name
        taken: dict[str, dict[str, Any]] = {}
        for row in sorted(rows, key=lambda row: (row["xmlid"] or "", row["model"])):
            xmlid = row["xmlid"]
            if xmlid is None:
                continue
            if xmlid in taken:
                self.report.collisions.append(xmlid)
                index = 2
                while f"{xmlid}_{index}" in taken:
                    index += 1
                row["xmlid"] = f"{xmlid}_{index}"
            taken[row["xmlid"]] = row
        xmlid_map: dict[str, list[str]] = defaultdict(list)
        source_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in [*rows, *self._absorbed]:
            targets = ([row] if row["ops"] else []) + row.get("absorbed_by", [])
            for source in row["sources"]:
                for target in targets:
                    if all(target is not kept for kept in source_map[source]):
                        source_map[source].append(target)
                if "#" in source:
                    continue
                for target in targets:
                    if target.get("xmlid") and target["xmlid"] not in xmlid_map[source]:
                        xmlid_map[source].append(target["xmlid"])
        self.report.source_map = dict(source_map)
        self.report.xmlid_map = {
            source: sorted(targets) for source, targets in sorted(xmlid_map.items())
        }

    def old_effective(self, model: str, op: str, groups: frozenset[str]) -> Effective:
        if not any(
            op in acl.ops and acl.group in groups for acl in self.acls.get(model, ())
        ):
            return Effective.of((), None)
        guards, grants = set(), set()
        for rule in self.rules.get(model, ()):
            if op not in rule.ops:
                continue
            if not rule.group:
                guards.add(rule.domain)
            elif rule.group in groups:
                (guards if rule.restrict else grants).add(rule.domain)
        return Effective.of(guards, grants or {TRUE})

    @staticmethod
    def new_effective(
        rows: Iterable[Mapping[str, Any]], op: str, groups: frozenset[str]
    ) -> Effective:
        guards, grants = set(), set()
        for row in rows:
            if op not in row["operation"]:
                continue
            if row["kind"] == "permission":
                if row["group"] in groups and row["domain"] != NOTHING:
                    grants.add(row["domain"])
            elif row["guard_scope"] == "everyone" or row["group"] in groups:
                guards.add(row["domain"])
        return Effective.of(guards, grants or None)

    def _principals(self, relevant: frozenset[str]) -> dict[frozenset[str], str]:
        principals: dict[frozenset[str], str] = {}

        def admit(closure: frozenset[str], label: str) -> None:
            if len(closure & EXCLUSIVE_GROUPS) > 1:
                return
            principals.setdefault(closure & relevant, label)

        for group in sorted(relevant):
            admit(self.closure[group], group)
        for first, second in itertools.combinations(sorted(relevant), 2):
            admit(self.closure[first] | self.closure[second], f"{first} + {second}")
        for group in sorted(self.closure):
            if len(self.closure[group] & relevant) > 1:
                admit(self.closure[group], group)
        return principals

    def _audit(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            row["operation"] = operation_string(row.pop("ops"))
        rows_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            rows_by_model[row["model"]].append(row)
        for model in sorted(set(self.acls) | set(self.rules)):
            relevant = frozenset(
                {acl.group for acl in self.acls.get(model, ())}
                | {rule.group for rule in self.rules.get(model, ()) if rule.group}
                | {GROUP_EVERYONE}
            )
            if len(relevant) < 2:
                continue
            new_rows = rows_by_model.get(model, [])
            self._audit_monotonicity(model, relevant, new_rows)
            self._audit_changes(model, relevant, new_rows)

    def _audit_monotonicity(self, model, relevant, new_rows) -> None:
        found: dict[tuple, set[str]] = defaultdict(set)
        for first, second in itertools.permutations(sorted(relevant), 2):
            alone = self.closure[first]
            both = alone | self.closure[second]
            if len(both & EXCLUSIVE_GROUPS) > 1 or both == alone:
                continue
            for op in OPERATIONS:
                before = self.old_effective(model, op, alone)
                after = self.old_effective(model, op, both)
                if before.sees_all and not after.sees_all and after.grants is not None:
                    new = self.new_effective(new_rows, op, both)
                    found[first, second, before, after, new].add(op)
        for (first, second, before, after, new), ops in sorted(
            found.items(), key=lambda item: (item[0][0], item[0][1])
        ):
            self.report.monotonicity.append(
                {
                    "model": model,
                    "alone": first,
                    "added": second,
                    "operation": operation_string(ops),
                    "added_has_access": any(
                        self.old_effective(model, op, self.closure[second]).grants
                        is not None
                        for op in ops
                    ),
                    "roles": sorted(
                        (self.closure[first] | self.closure[second]) & EXCLUSIVE_GROUPS
                    ),
                    "old_alone": before.render(),
                    "old_both": after.render(),
                    "new_both": new.render(),
                }
            )

    def _audit_changes(self, model, relevant, new_rows) -> None:
        found: dict[tuple, set[str]] = defaultdict(set)
        for groups, label in self._principals(relevant).items():
            closure = groups | {GROUP_EVERYONE}
            for op in OPERATIONS:
                old = self.old_effective(model, op, closure)
                new = self.new_effective(new_rows, op, closure)
                if old != new:
                    found[label, old, new].add(op)
        for (label, old, new), ops in sorted(
            found.items(), key=lambda item: item[0][0]
        ):
            self.report.changes.append(
                {
                    "model": model,
                    "principal": label,
                    "operation": operation_string(ops),
                    "old": old.render(),
                    "new": new.render(),
                    "direction": _direction(old, new),
                }
            )


def _direction(old: Effective, new: Effective) -> str:
    if old.guards != new.guards:
        return "guards differ"
    if old.grants is None:
        return "widens"
    if new.grants is None:
        return "narrows"
    if new.sees_all and not old.sees_all:
        return "widens"
    if old.sees_all and not new.sees_all:
        return "narrows"
    if old.grants < new.grants:
        return "widens"
    if new.grants < old.grants:
        return "narrows"
    return "differs"


def convert(
    acl_lines: Sequence[Mapping[str, Any]],
    rules: Sequence[Mapping[str, Any]],
    group_implications: Mapping[str, Iterable[str]],
    *,
    module_deps: Mapping[str, Iterable[str]] | None = None,
) -> tuple[list[dict[str, Any]], ConversionReport]:
    converter = _Converter(acl_lines, rules, group_implications, module_deps)
    rows = [
        {
            "xmlid": row["xmlid"],
            "module": row["module"],
            "name": row["name"],
            "model": row["model"],
            "kind": row["kind"],
            "guard_scope": row["guard_scope"],
            "group": row["group"],
            "operation": row["operation"],
            "domain": row["domain"],
            "sources": row["sources"],
            "deactivated_by": list(row["conditional"]),
            "noupdate": row["noupdate"],
        }
        for row in converter.convert()
    ]
    return rows, converter.report


def synthesize(
    acl_lines: Sequence[Mapping[str, Any]],
    rules: Sequence[Mapping[str, Any]],
    group_implications: Mapping[str, Iterable[str]],
) -> list[dict[str, Any]]:
    converter = _Converter(acl_lines, rules, group_implications, None)
    return [
        {
            "kind": row["kind"],
            "model": row["model"],
            "group": row["group"],
            "guard_scope": row["guard_scope"],
            "operation": operation_string(row["ops"]),
            "domain": row["domain"],
            "name": row["name"],
            "from_rule": row["from_rule"],
        }
        for model in sorted(set(converter.acls) | set(converter.rules))
        for row in converter._convert_model(model)
    ]


_PERM_COLUMNS = ("perm_read", "perm_write", "perm_create", "perm_unlink")


def _xmlids(cr: Any) -> dict[tuple[str, int], str]:
    cr.execute(
        """
        SELECT DISTINCT ON (d.model, d.res_id) d.model, d.res_id,
               d.module || '.' || d.name
          FROM ir_model_data d
         WHERE d.model IN ('res.groups', 'ir.model.access', 'ir.rule')
         ORDER BY d.model, d.res_id, d.id
        """
    )
    return {(model, res_id): xmlid for model, res_id, xmlid in cr.fetchall()}


def _noupdate(cr: Any) -> set[tuple[str, int]]:
    cr.execute(
        """
        SELECT d.model, d.res_id
          FROM ir_model_data d
         WHERE d.model IN ('ir.model.access', 'ir.rule') AND d.noupdate
        """
    )
    return set(cr.fetchall())


def group_keys(cr: Any, group_ids: Iterable[int]) -> frozenset[str]:
    xmlids = _xmlids(cr)
    return frozenset(
        xmlids.get(("res.groups", group_id)) or f"res.groups#{group_id}"
        for group_id in group_ids
    ) | {GROUP_EVERYONE}


def reach(
    rows: Iterable[Mapping[str, Any]], operation: str, groups: frozenset[str]
) -> Effective:
    return _Converter.new_effective(rows, operation, groups)


def read_database(
    cr: Any, models: Iterable[str] | None = None
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, set[str]],
    dict[str, set[str]],
]:
    wanted = sorted(models) if models is not None else None
    xmlids = _xmlids(cr)
    noupdate = _noupdate(cr)

    def group_key(group_id: int) -> str:
        return xmlids.get(("res.groups", group_id)) or f"res.groups#{group_id}"

    cr.execute(
        """
        SELECT a.id, a.name, m.model, a.group_id, a.active,
               a.perm_read, a.perm_write, a.perm_create, a.perm_unlink
          FROM ir_model_access a
          JOIN ir_model m ON m.id = a.model_id
         WHERE %s::text[] IS NULL OR m.model = ANY(%s::text[])
         ORDER BY a.id
        """,
        (wanted, wanted),
    )
    acl_lines = []
    for row in cr.fetchall():
        access_id, name, model, group_id, active, *perms = row
        perms = dict(zip(_PERM_COLUMNS, perms, strict=True))
        acl_lines.append(
            {
                "id": access_id,
                "xmlid": xmlids.get(("ir.model.access", access_id)),
                "noupdate": ("ir.model.access", access_id) in noupdate,
                "name": name,
                "model": model,
                "group": group_key(group_id) if group_id else None,
                "active": active,
                **perms,
            }
        )
    cr.execute(
        """
        SELECT r.id, r.name, m.model, r.domain_force, r.composition, r.active,
               r.global, r.perm_read, r.perm_write, r.perm_create, r.perm_unlink,
               ARRAY(SELECT g.group_id FROM rule_group_rel g
                      WHERE g.rule_group_id = r.id ORDER BY g.group_id)
          FROM ir_rule r
          JOIN ir_model m ON m.id = r.model_id
         WHERE %s::text[] IS NULL OR m.model = ANY(%s::text[])
         ORDER BY r.id
        """,
        (wanted, wanted),
    )
    rules = []
    for row in cr.fetchall():
        rule_id, name, model, domain, composition, active, is_global, *rest = row
        *perms, group_ids = rest
        perms = dict(zip(_PERM_COLUMNS, perms, strict=True))
        rules.append(
            {
                "id": rule_id,
                "xmlid": xmlids.get(("ir.rule", rule_id)),
                "noupdate": ("ir.rule", rule_id) in noupdate,
                "name": name,
                "model": model,
                "domain_force": domain,
                "composition": composition,
                "active": active,
                "global": is_global,
                "groups": [group_key(group_id) for group_id in group_ids],
                **perms,
            }
        )
    cr.execute("SELECT gid, hid FROM res_groups_implied_rel")
    implications: dict[str, set[str]] = defaultdict(set)
    for group_id, implied_id in cr.fetchall():
        implications[group_key(group_id)].add(group_key(implied_id))
    cr.execute(
        """
        SELECT m.name, d.name
          FROM ir_module_module m
          LEFT JOIN ir_module_module_dependency d ON d.module_id = m.id
         WHERE m.state IN ('installed', 'to upgrade', 'to remove')
        """
    )
    direct: dict[str, set[str]] = defaultdict(set)
    for module, dependency in cr.fetchall():
        direct.setdefault(module, set())
        if dependency:
            direct[module].add(dependency)
    module_deps: dict[str, set[str]] = {}
    for module in direct:
        seen = {module}
        todo = [module]
        while todo:
            for dependency in direct.get(todo.pop(), ()):
                if dependency not in seen:
                    seen.add(dependency)
                    todo.append(dependency)
        module_deps[module] = seen
    return acl_lines, rules, dict(implications), module_deps
