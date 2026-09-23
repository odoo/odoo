import argparse
import ast
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from lxml import etree

try:
    from . import _ir_access_audit as audit
    from . import _pretty_xml, _sort_xml_records
except ImportError:
    import _ir_access_audit as audit
    import _pretty_xml
    import _sort_xml_records

ir_access_convert = audit.ir_access_convert

PERMS = audit.PERMS
CSV_NAME = "security/ir.access.csv"
XML_NAME = "security/ir_access.xml"
CSV_HEADER = ["id", "name", "model_id/id", "group_id/id", "kind", "operation", "domain"]
_MODEL_NAME_RE = re.compile(
    r"""^\s+_name\s*(?::[^=]+)?=\s*(["'])([\w.]+)\1""", re.MULTILINE
)
_ACCESS_CSV_RE = re.compile(r"(^|/)ir\.model\.access[^/]*\.csv$")
_DATA_KEYS = ("data", "demo")


@dataclass
class Source:
    kind: str
    xmlid: str
    module: str
    entry: str
    order: tuple[int, int, int]
    values: dict
    noupdate: bool = False
    line: int = 0


@dataclass
class Module:
    name: str
    path: Path
    manifest: dict
    index: int
    entries: list[tuple[str, str]] = field(default_factory=list)


def discover(roots: list[Path]) -> dict[str, Module]:
    modules: dict[str, Module] = {}
    for root in roots:
        for manifest in sorted(root.glob("*/__manifest__.py")):
            name = manifest.parent.name
            if name in modules:
                continue
            data = ast.literal_eval(manifest.read_text())
            modules[name] = Module(name, manifest.parent, data, 0)
    return modules


def model_index(modules: dict[str, Module]) -> dict[str, set[str]]:
    defined: dict[str, set[str]] = defaultdict(set)
    for module in modules.values():
        for source in module.path.rglob("*.py"):
            text = source.read_text(errors="replace")
            for match in _MODEL_NAME_RE.finditer(text):
                defined[match[2]].add(module.name)
    return defined


def overridden(values: dict, source: Source, fields=None) -> dict:
    values = {**values, "groups": list(values.get("groups") or ())}
    new = source.values
    if fields is None:
        fields = new.get("fields")
    if fields is None:
        for key in ("name", "model", "model_ref", "group", *PERMS):
            values[key] = new[key]
        return values
    for name in fields:
        if name == "groups":
            values["groups"] = sorted(
                audit.apply_commands(set(values["groups"]), new["group_commands"])
            )
        elif name == "domain_force":
            values["domain_force"] = new.get("domain_force")
        elif name == "model_id":
            values["model"] = new["model"]
            values["model_ref"] = new["model_ref"]
        elif name in PERMS or name in ("name", "active", "composition", "group_id"):
            key = "group" if name == "group_id" else name
            values[key] = new[key]
    return values


def is_noupdate(node) -> bool:
    for ancestor in node.iterancestors():
        value = ancestor.get("noupdate")
        if value is not None:
            return value.strip().lower() in ("1", "true")
    return False


class Collector:
    def __init__(self, roots: list[Path]):
        self.modules = discover(roots)
        closures = audit.dependency_closure(
            {name: (m.path, m.manifest) for name, m in self.modules.items()}
        )
        self.closures = closures
        self.order = sorted(self.modules, key=lambda n: (len(closures[n]), n))
        for index, name in enumerate(self.order):
            self.modules[name].index = index
        self.defined = model_index(self.modules)
        self.acls: dict[str, Source] = {}
        self.rules: dict[str, Source] = {}
        self.overrides: list[Source] = []
        self.implied: dict[str, set[str]] = defaultdict(set)
        self.edges: list[tuple[str, str, str, list[str]]] = []
        self.problems: list[tuple[str, str]] = []
        self.files: dict[str, dict[Path, str]] = defaultdict(dict)

    def model(self, module: str, node) -> tuple[str | None, str | None]:
        # the model is keyed by its external id's local name, which the rules
        # that search it by name share: dynamic test models have no literal
        # _name to read
        if isinstance(node, str) or node is None:
            ref = node
        elif node.get("search"):
            for leaf in ast.literal_eval(node.get("search")):
                if leaf[0] == "model" and leaf[1] == "=":
                    local = f"model_{leaf[2].replace('.', '_')}"
                    owners = [
                        name
                        for name in self.defined.get(leaf[2], ())
                        if name in self.closures.get(module, ())
                    ]
                    if not owners:
                        self.problems.append(
                            (f"{module}:{leaf[2]}", "searched model defined nowhere")
                        )
                        return None, None
                    return local, f"{min(owners, key=self.order.index)}.{local}"
            return None, None
        else:
            ref = node.get("ref")
        if not ref:
            return None, None
        qualified = audit.qualify(module, ref)
        return qualified.partition(".")[2], qualified

    def run(self) -> None:
        for name in self.order:
            module = self.modules[name]
            for key in _DATA_KEYS:
                for entry in module.manifest.get(key, ()):
                    module.entries.append((key, entry))
                    file = module.path / entry
                    if not file.exists():
                        continue
                    order = (module.index, len(module.entries), 0)
                    if _ACCESS_CSV_RE.search(entry):
                        self.read_csv(module, entry, file, order)
                    elif entry.endswith(".xml"):
                        self.read_xml(module, entry, file, order)

    def read_csv(self, module: Module, entry: str, file: Path, order) -> None:
        self.files[module.name][file] = entry
        with file.open(newline="", encoding="utf-8") as stream:
            for number, line in enumerate(csv.DictReader(stream)):
                if not line.get("id"):
                    self.problems.append((str(file), "access line without id"))
                    continue
                xmlid = audit.qualify(module.name, line["id"])
                model_ref = line.get("model_id:id") or line.get("model_id/id")
                group_ref = line.get("group_id:id") or line.get("group_id/id")
                model, model_ref = self.model(module.name, model_ref)
                values = {
                    "xmlid": xmlid,
                    "module": xmlid.partition(".")[0],
                    "name": line.get("name") or None,
                    "model": model,
                    "model_ref": model_ref,
                    "group": audit.qualify(module.name, group_ref)
                    if group_ref
                    else None,
                    "active": True,
                }
                for perm in PERMS:
                    values[perm] = (line.get(perm) or "0").strip() not in ("0", "")
                source = Source(
                    "acl",
                    xmlid,
                    module.name,
                    entry,
                    (order[0], order[1], number),
                    values,
                    line=number + 2,
                )
                if not xmlid.startswith(f"{module.name}."):
                    self.overrides.append(source)
                elif xmlid in self.acls:
                    self.problems.append((xmlid, "access line declared twice"))
                else:
                    self.acls[xmlid] = source

    def read_xml(self, module: Module, entry: str, file: Path, order) -> None:
        try:
            tree = etree.parse(str(file))
        except etree.XMLSyntaxError as error:
            self.problems.append((str(file), f"unparsable XML: {error}"))
            return
        for number, record in enumerate(tree.iter("record")):
            kind = record.get("model")
            if kind not in ("ir.model.access", "ir.rule", "res.groups"):
                continue
            xmlid = audit.qualify(module.name, record.get("id"))
            if xmlid is None:
                self.problems.append((str(file), f"{kind} record without id"))
                continue
            if kind == "res.groups":
                self.xml_res_groups(module.name, xmlid, record)
                continue
            self.files[module.name][file] = entry
            fields = {node.get("name"): node for node in record.findall("field")}
            source = Source(
                "acl" if kind == "ir.model.access" else "rule",
                xmlid,
                module.name,
                entry,
                (order[0], order[1], number),
                {"xmlid": xmlid, "module": xmlid.partition(".")[0]},
                noupdate=is_noupdate(record),
                line=record.sourceline,
            )
            try:
                if kind == "ir.model.access":
                    self.xml_acl(module.name, fields, source.values)
                else:
                    self.xml_rule(module.name, fields, source.values)
            except (ValueError, SyntaxError, AttributeError, IndexError) as error:
                self.problems.append((xmlid, f"unreadable {kind} record: {error}"))
                continue
            source.values["noupdate"] = source.noupdate
            target = self.acls if source.kind == "acl" else self.rules
            if not xmlid.startswith(f"{module.name}."):
                source.values["fields"] = sorted(fields)
                self.overrides.append(source)
            elif xmlid in target:
                self.problems.append((xmlid, f"{kind} declared twice, merged"))
                self.merge(target[xmlid], fields, source)
            else:
                target[xmlid] = source

    def merge(self, first: Source, fields, second: Source) -> None:
        first.values = overridden(first.values, second, fields)

    def xml_acl(self, module: str, fields, values: dict) -> None:
        values.update(dict.fromkeys(PERMS, False), group=None, active=True)
        if "name" in fields:
            values["name"] = fields["name"].text
        if "model_id" in fields:
            values["model"], values["model_ref"] = self.model(
                module, fields["model_id"]
            )
        if "group_id" in fields:
            values["group"] = audit.qualify(module, fields["group_id"].get("ref"))
        for perm in PERMS:
            if perm in fields:
                values[perm] = audit.read_bool(fields[perm])
        if "active" in fields:
            values["active"] = audit.read_bool(fields["active"])

    def xml_rule(self, module: str, fields, values: dict) -> None:
        values.update(dict.fromkeys(PERMS), groups=[], active=True)
        if "name" in fields:
            values["name"] = fields["name"].text
        if "model_id" in fields:
            values["model"], values["model_ref"] = self.model(
                module, fields["model_id"]
            )
        if "domain_force" in fields:
            node = fields["domain_force"]
            if node.get("eval") is not None:
                raise ValueError("domain_force given by eval")
            values["domain_force"] = node.text
        if "groups" in fields:
            commands = audit.GroupCommands(module).parse(
                fields["groups"].get("eval") or "[]"
            )
            values["group_commands"] = commands
            values["groups"] = sorted(audit.apply_commands(set(), commands))
        for perm in PERMS:
            if perm in fields:
                values[perm] = audit.read_bool(fields[perm])
        if "active" in fields:
            values["active"] = audit.read_bool(fields["active"])
        if "composition" in fields:
            values["composition"] = (fields["composition"].text or "").strip()

    def xml_res_groups(self, module: str, xmlid: str, record) -> None:
        fields = {node.get("name"): node for node in record.findall("field")}
        self.implied.setdefault(xmlid, set())
        if (node := fields.get("implied_ids")) is not None and node.get("eval"):
            for verb, refs in audit.GroupCommands(module).parse(node.get("eval")):
                self.edges.append((module, verb, xmlid, refs))
            commands = audit.GroupCommands(module).parse(node.get("eval"))
            self.implied[xmlid] = audit.apply_commands(self.implied[xmlid], commands)
        if (node := fields.get("implied_by_ids")) is not None and node.get("eval"):
            for verb, refs in audit.GroupCommands(module).parse(node.get("eval")):
                for ref in refs:
                    self.edges.append((module, verb, ref, [xmlid]))
                    if verb == "link":
                        self.implied[ref].add(xmlid)
                    elif verb == "unlink":
                        self.implied[ref].discard(xmlid)

    def implications(self, installed: set[str]) -> dict[str, set[str]]:
        implied: dict[str, set[str]] = defaultdict(set)
        for module, verb, group, refs in self.edges:
            if module not in installed:
                continue
            if verb == "link":
                implied[group].update(refs)
            elif verb == "unlink":
                implied[group].difference_update(refs)
            elif verb == "set":
                implied[group] = set(refs)
            elif verb == "clear":
                implied[group] = set()
        return implied

    @property
    def static_implied(self) -> dict[str, set[str]]:
        # an implication a module declares between two groups of other modules
        # holds only where it is installed (accountant makes the accounting
        # manager imply the accountant): the rows of those modules cannot count
        # on it, and where it holds, the database's implications give its
        # members the rows of both groups anyway
        implied: dict[str, set[str]] = defaultdict(set)
        for module, verb, group, refs in self.edges:
            refs = [
                ref
                for ref in refs
                if module in (group.partition(".")[0], ref.partition(".")[0])
            ]
            if verb == "link":
                implied[group].update(refs)
            elif verb == "unlink":
                implied[group].difference_update(refs)
            elif verb == "set":
                implied[group] = set(refs)
            elif verb == "clear":
                implied[group] = set()
        for group in self.implied:
            implied.setdefault(group, set())
        return implied

    def convert(self):
        acls = [source.values for source in self.acls.values()]
        rules = [source.values for source in self.rules.values()]
        return ir_access_convert.convert(
            acls, rules, self.static_implied, module_deps=self.closures
        )


def flat_domain(domain: str) -> str:
    return " ".join(line.strip() for line in domain.splitlines() if line.strip())


def local_ref(module: str, xmlid: str) -> str:
    return xmlid.removeprefix(f"{module}.")


def row_order(collector: Collector, row: dict) -> tuple:
    # a row stands where its access line stood, the rows a rule narrows it to
    # right after it; a guard where its rule stood, after every access line
    acl_orders = [
        collector.acls[key].order for key in row["sources"] if key in collector.acls
    ]
    rule_orders = [
        collector.rules[key].order for key in row["sources"] if key in collector.rules
    ]
    if acl_orders:
        return (0, min(acl_orders), min(rule_orders, default=(0, 0, 0)), row["xmlid"])
    return (1, min(rule_orders, default=(0, 0, 0)), (0, 0, 0), row["xmlid"])


def model_ref(collector: Collector, row: dict) -> str:
    for key in row["sources"]:
        source = collector.acls.get(key) or collector.rules.get(key)
        if source is not None and source.values.get("model_ref"):
            return source.values["model_ref"]
    raise ValueError(f"no model reference for {row['xmlid']}")


def render_csv(collector: Collector, module: str, rows: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for row in rows:
        writer.writerow(
            [
                local_ref(module, row["xmlid"]),
                row["name"],
                local_ref(module, model_ref(collector, row)),
                local_ref(module, row["group"]),
                row["kind"],
                row["operation"],
                flat_domain(row["domain"]),
            ]
        )
    return output.getvalue()


def render_xml(records: list[str], noupdate_records: list[str]) -> str:
    parts = ["\n\n".join(records)] if records else []
    if noupdate_records:
        body = "\n\n".join(
            "\n".join(f"    {line}" if line else line for line in record.splitlines())
            for record in noupdate_records
        )
        parts.append(f'    <data noupdate="1">\n{body}\n    </data>')
    body = "\n\n".join(parts)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n\n{body}\n\n</odoo>\n'


def deactivation(xmlid: str) -> str:
    return (
        f'    <record id="{xmlid}" model="ir.access">\n'
        f'        <field name="active" eval="False" />\n'
        f"    </record>"
    )


def xml_fields(collector: Collector, module: str, row: dict, names) -> list[str]:
    fields = []
    for name in names:
        value = row[name]
        if name == "model":
            ref = local_ref(module, model_ref(collector, row))
            fields.append(f'<field name="model_id" ref="{ref}" />')
        elif name == "group":
            fields.append(f'<field name="group_id" ref="{local_ref(module, value)}" />')
        elif name == "active":
            fields.append(f'<field name="active" eval="{value}" />')
        elif name == "guard_scope" and not value:
            continue
        else:
            text = flat_domain(value) if name == "domain" else value
            fields.append(f'<field name="{name}">{escape(text)}</field>')
    return fields


def xml_record(xmlid: str, fields: list[str]) -> str:
    body = "\n".join(f"        {field}" for field in fields)
    return f'    <record id="{xmlid}" model="ir.access">\n{body}\n    </record>'


def element_span(lines: list[str], node) -> tuple[int, int]:
    start = node.sourceline - 1
    if isinstance(node, etree._Comment):
        # lxml numbers a comment by the line it ends on
        end = start
        while "<!--" not in lines[start]:
            start -= 1
        return start, end
    tag = node.tag
    # and an element by the line its start tag ends on
    while not re.search(rf"<{tag}(\s|>|/>|$)", lines[start]):
        start -= 1
    end = start
    depth = 0
    opening = re.compile(rf"<{tag}(\s|>|/>|$)")
    closing = f"</{tag}>"
    while True:
        text = lines[end]
        depth += len(opening.findall(text))
        depth -= text.count(closing)
        if depth <= 0 and (closing in text or re.search(r"/>\s*$", text)):
            if depth <= 0:
                return start, end
        end += 1


def strip_records(file: Path, xmlids: set[str], module: str) -> bool:
    text = file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = etree.parse(str(file))
    drop: set[int] = set()
    for record in tree.iter("record"):
        xmlid = audit.qualify(module, record.get("id"))
        if xmlid not in xmlids or record.get("model") not in (
            "ir.model.access",
            "ir.rule",
        ):
            continue
        start, end = element_span(lines, record)
        drop.update(range(start, end + 1))
        previous = record.getprevious()
        while (
            previous is not None
            and isinstance(previous, etree._Comment)
            and not (previous.tail or "").count("\n") > 1
        ):
            start, end = element_span(lines, previous)
            drop.update(range(start, end + 1))
            previous = previous.getprevious()
    kept = [line for index, line in enumerate(lines) if index not in drop]
    text = "".join(kept)
    while True:
        tree = etree.fromstring(text.encode())
        lines = text.splitlines(keepends=True)
        empty = [
            node
            for node in tree.iter("data")
            if not [child for child in node if not isinstance(child, etree._Comment)]
        ]
        if not empty:
            break
        drop = set()
        for node in empty:
            start, end = element_span(lines, node)
            drop.update(range(start, end + 1))
        text = "".join(line for index, line in enumerate(lines) if index not in drop)
    tree = etree.fromstring(text.encode())
    if not [child for child in tree if not isinstance(child, etree._Comment)]:
        file.unlink()
        return False
    text = re.sub(r"\n{3,}", "\n\n", text)
    file.write_text(text, encoding="utf-8")
    return True


class ManifestEditor:
    def __init__(self, path: Path):
        self.path = path
        self.text = path.read_text(encoding="utf-8")

    def _find(self, entry: str) -> re.Match:
        pattern = re.compile(
            r"^(?P<indent>[ \t]*)(?P<quote>['\"])"
            + re.escape(entry)
            + r"(?P=quote),?[ \t]*(#.*)?\n",
            re.MULTILINE,
        )
        matches = list(pattern.finditer(self.text))
        if len(matches) != 1:
            raise ValueError(f"{self.path}: {entry!r} found {len(matches)} times")
        return matches[0]

    def remove(self, entry: str) -> None:
        match = self._find(entry)
        self.text = self.text[: match.start()] + self.text[match.end() :]

    def replace(self, entry: str, new: str) -> None:
        match = self._find(entry)
        line = f'{match["indent"]}"{new}",\n'
        self.text = self.text[: match.start()] + line + self.text[match.end() :]

    def insert_after(self, entry: str, new: str) -> None:
        match = self._find(entry)
        line = f'{match["indent"]}"{new}",\n'
        self.text = self.text[: match.end()] + line + self.text[match.end() :]

    def insert_first(self, new: str) -> None:
        tree = ast.parse(self.text, mode="eval").body
        keys = {
            key.value: value for key, value in zip(tree.keys, tree.values, strict=True)
        }
        lines = self.text.splitlines(keepends=True)
        if "data" in keys:
            value = keys["data"]
            if value.elts:
                first = value.elts[0]
                indent = re.match(r"[ \t]*", lines[first.lineno - 1])[0]
                lines.insert(first.lineno - 1, f'{indent}"{new}",\n')
            else:
                line = lines[value.lineno - 1]
                lines[value.lineno - 1] = line.replace("[]", f'["{new}"]', 1)
        else:
            before = [
                k
                for k in ("depends", "external_dependencies", "countries")
                if k in keys
            ]
            anchor = keys[before[-1]] if before else tree.values[-1]
            indent = re.match(r"[ \t]*", lines[anchor.lineno - 1])[0] or "    "
            lines.insert(
                anchor.end_lineno,
                f'{indent}"data": [\n{indent}    "{new}",\n{indent}],\n',
            )
        self.text = "".join(lines)

    def save(self) -> None:
        ast.literal_eval(self.text)
        self.path.write_text(self.text)


ROW_FIELDS = ("name", "model", "group", "kind", "guard_scope", "operation", "domain")


def sources_with_overrides(collector: Collector, installed, skip: str | None = None):
    acls = {key: dict(source.values) for key, source in collector.acls.items()}
    rules = {key: dict(source.values) for key, source in collector.rules.items()}
    for source in sorted(collector.overrides, key=lambda s: s.order):
        if source.module not in installed or source.module == skip:
            continue
        target = acls if source.kind == "acl" else rules
        if source.xmlid not in target:
            raise ValueError(f"{source.module} overrides unknown {source.xmlid}")
        target[source.xmlid] = overridden(target[source.xmlid], source)
    return acls, rules


def override_plan(collector: Collector) -> dict[str, dict]:
    # what each module that overrode another module's access line or rule by
    # external id now overrides: the rows the conversion makes differently
    # with its override than without, among the rows it can reference
    plans: dict[str, dict] = {}
    for module in sorted(
        {source.module for source in collector.overrides},
        key=lambda name: collector.modules[name].index,
    ):
        closure = collector.closures[module]
        converted = []
        for skip in (module, None):
            acls, rules = sources_with_overrides(collector, closure, skip)
            rows, _report = ir_access_convert.convert(
                list(acls.values()),
                list(rules.values()),
                collector.static_implied,
                module_deps=collector.closures,
            )
            converted.append({row["xmlid"]: row for row in rows})
        before, after = converted
        entry = {"write": {}, "create": [], "deactivate": [], "outside": []}
        for xmlid in sorted(set(before) | set(after)):
            old, new = before.get(xmlid), after.get(xmlid)
            row_module = (new or old)["module"]
            if old and new:
                changed = {f: new[f] for f in ROW_FIELDS if old[f] != new[f]}
                if old["deactivated_by"] != new["deactivated_by"]:
                    changed["deactivated_by"] = new["deactivated_by"]
                if not changed:
                    continue
            if row_module not in closure:
                entry["outside"].append(xmlid)
            elif old and new:
                entry["write"][xmlid] = changed
            elif new:
                entry["create"].append(
                    {
                        **new,
                        "xmlid": f"{module}.{xmlid.partition('.')[2]}",
                        "module": module,
                    }
                )
            else:
                entry["deactivate"].append(xmlid)
        plans[module] = entry
    return plans


def toggled_rows(collector: Collector) -> list[dict]:
    # a module that ships an access line and a rule inactive and switches them
    # on at runtime gets the rows they make together, inactive
    sources = [*collector.acls.values(), *collector.rules.values()]
    rows = []
    for module in sorted(
        {s.module for s in sources if not s.values.get("active", True)}
    ):
        converted = []
        for activate in (False, True):
            acls = [
                {**s.values, "active": True}
                if activate and s.module == module
                else s.values
                for s in collector.acls.values()
            ]
            rules = [
                {**s.values, "active": True}
                if activate and s.module == module
                else s.values
                for s in collector.rules.values()
            ]
            result, _report = ir_access_convert.convert(
                acls, rules, collector.static_implied, module_deps=collector.closures
            )
            converted.append({row["xmlid"]: row for row in result})
        before, after = converted
        for xmlid, row in after.items():
            if before.get(xmlid) != row:
                if xmlid in before or row["module"] != module:
                    raise ValueError(f"activating {module}'s rows changes {xmlid}")
                rows.append({**row, "active": False})
    return rows


def bridge(collector: Collector, first: str, second: str) -> str | None:
    # a module installed whenever both are: it depends on both and installs by
    # itself once the modules it waits for, all loaded with the two, are there
    loaded = collector.closures[first] | collector.closures[second]
    candidates = []
    for name in collector.order:
        module = collector.modules[name]
        if not {first, second} <= collector.closures[name]:
            continue
        trigger = module.manifest.get("auto_install")
        if trigger is True:
            trigger = module.manifest.get("depends", [])
        if not trigger or not set(trigger) <= loaded:
            continue
        candidates.append(name)
    minimal = [
        name
        for name in candidates
        if not any(
            other != name and other in collector.closures[name] for other in candidates
        )
    ]
    return minimal[0] if minimal else None


def placed_in_bridges(collector: Collector, report) -> tuple[list[dict], list[dict]]:
    rows, left = [], []
    for entry in report.unplaced:
        acl = collector.acls[entry["acl"]]
        rule = collector.rules[entry["rule"]]
        module = bridge(collector, acl.module, rule.module)
        if module is None:
            left.append(entry)
            continue
        local = rule.xmlid.partition(".")[2]
        if tuple(rule.values.get("groups") or ()) != (entry["group"],):
            local = f"{local}_{entry['group'].rpartition('.')[2]}"
        rows.append(
            {
                "xmlid": f"{module}.{local}",
                "module": module,
                "name": rule.values.get("name") or rule.values["model"],
                "model": entry["model"],
                "kind": "permission",
                "guard_scope": None,
                "group": entry["group"],
                "operation": entry["operation"],
                "domain": ir_access_convert.normalize_domain(
                    rule.values.get("domain_force")
                ),
                "sources": [acl.xmlid, rule.xmlid],
                "deactivated_by": [],
                "noupdate": rule.noupdate,
            }
        )
    merged: dict[str, dict] = {}
    for row in rows:
        if row["xmlid"] in merged:
            kept = merged[row["xmlid"]]
            kept["operation"] = ir_access_convert.operation_string(
                set(kept["operation"]) | set(row["operation"])
            )
            kept["sources"] += [s for s in row["sources"] if s not in kept["sources"]]
        else:
            merged[row["xmlid"]] = row
    return list(merged.values()), left


def plan(collector: Collector, rows: list[dict], report=None) -> dict:
    left = []
    if report is not None:
        extra, left = placed_in_bridges(collector, report)
        rows = [*rows, *extra]
        for row in extra:
            for source in row["sources"]:
                targets = report.xmlid_map.setdefault(source, [])
                if row["xmlid"] not in targets:
                    targets.append(row["xmlid"])
    writes: dict[str, dict[str, dict]] = {}
    override_deactivations: dict[str, list[str]] = defaultdict(list)
    outside = []
    for module, entry in override_plan(collector).items():
        closure = collector.closures[module]
        rows = [
            *rows,
            *(
                row
                for row in entry["create"]
                if not set(row["deactivated_by"]) & closure
            ),
        ]
        override_deactivations[module] += entry["deactivate"]
        writes[module] = entry["write"]
        outside += [(module, xmlid) for xmlid in entry["outside"]]
    toggled = toggled_rows(collector)
    by_module: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["xmlid"] is None or row["module"] is None:
            raise ValueError(f"row without module: {row}")
        by_module[row["module"]].append(row)
    deactivations: dict[str, list[str]] = defaultdict(list)
    bridges = []
    for row in rows:
        for module in row["deactivated_by"]:
            if row["module"] in collector.closures.get(module, ()):
                deactivations[module].append(row["xmlid"])
            elif placed := bridge(collector, row["module"], module):
                deactivations[placed].append(row["xmlid"])
            else:
                bridges.append((row["xmlid"], module))
    for module, xmlids in override_deactivations.items():
        deactivations[module] += xmlids
    return {
        "rows": by_module,
        "all_rows": rows,
        "deactivations": deactivations,
        "writes": writes,
        "toggled": toggled,
        "bridges": bridges,
        "unplaced": left,
        "overrides outside their module's reach": outside,
    }


def apply(collector: Collector, rows: list[dict], report) -> dict:
    result = plan(collector, rows, report)
    touched_xml: set[Path] = set()
    stats = Counter()
    toggled: dict[str, list[dict]] = defaultdict(list)
    for row in result["toggled"]:
        toggled[row["module"]].append(row)
    modules = (
        set(result["rows"])
        | set(result["deactivations"])
        | set(result["writes"])
        | set(toggled)
        | set(collector.files)
    )
    for name in sorted(modules, key=lambda n: collector.modules[n].index):
        module = collector.modules[name]
        editor = ManifestEditor(module.path / "__manifest__.py")
        module_rows = sorted(
            result["rows"].get(name, []), key=lambda row: row_order(collector, row)
        )
        records = [
            deactivation(xmlid)
            for xmlid in sorted(result["deactivations"].get(name, []))
        ]
        for xmlid, changed in sorted(result["writes"].get(name, {}).items()):
            row = {
                **next(r for r in result["all_rows"] if r["xmlid"] == xmlid),
                **changed,
            }
            records.append(
                xml_record(
                    xmlid,
                    xml_fields(
                        collector, name, row, sorted(set(changed) & set(ROW_FIELDS))
                    ),
                )
            )
        noupdate_records = [
            xml_record(
                local_ref(name, row["xmlid"]),
                xml_fields(
                    collector,
                    name,
                    row,
                    (
                        "name",
                        "model",
                        "group",
                        "kind",
                        "guard_scope",
                        "active",
                        "operation",
                        "domain",
                    ),
                ),
            )
            for row in sorted(toggled.get(name, []), key=lambda row: row["xmlid"])
        ]
        removed: list[str] = []
        contributing: list[str] = []
        for file, entry in sorted(
            collector.files.get(name, {}).items(),
            key=lambda item: [e for _k, e in module.entries].index(item[1]),
        ):
            contributing.append(entry)
            if file.suffix == ".csv":
                file.unlink()
                removed.append(entry)
                stats["csv files removed"] += 1
                continue
            xmlids = {
                source.xmlid
                for source in [
                    *collector.acls.values(),
                    *collector.rules.values(),
                    *collector.overrides,
                ]
                if source.module == name and source.entry == entry
            }
            if strip_records(file, xmlids, name):
                touched_xml.add(file)
                stats["xml files kept"] += 1
            else:
                removed.append(entry)
                stats["xml files removed"] += 1
        new_entries = []
        if module_rows:
            path = module.path / CSV_NAME
            path.parent.mkdir(exist_ok=True)
            path.write_text(render_csv(collector, name, module_rows))
            new_entries.append(CSV_NAME)
            stats["csv files written"] += 1
            stats["rows written"] += len(module_rows)
        if records or noupdate_records:
            path = module.path / XML_NAME
            path.write_text(render_xml(records, noupdate_records))
            touched_xml.add(path)
            new_entries.append(XML_NAME)
            stats["xml records written"] += len(records) + len(noupdate_records)
        order = [entry for _key, entry in module.entries]
        anchor = max(contributing, key=order.index) if contributing else None
        if anchor is None and new_entries:
            editor.insert_first(new_entries[0])
            anchor, new_entries = new_entries[0], new_entries[1:]
        previous = anchor
        for index, entry in enumerate(new_entries):
            if index == 0 and anchor in removed:
                editor.replace(anchor, entry)
                removed.remove(anchor)
            else:
                editor.insert_after(previous, entry)
            previous = entry
        for entry in removed:
            editor.remove(entry)
        editor.save()
    for file in sorted(touched_xml):
        if _pretty_xml.is_formattable(file):
            _pretty_xml.format_xml_file(file)
            _sort_xml_records.sort_xml_file(file)
            _pretty_xml.format_xml_file(file)
    stats["xml files formatted"] = len(touched_xml)
    return {**result, "stats": dict(stats)}


def _verify_one(args) -> list[tuple]:
    collector, rows, deactivations, writes, installed, models = args
    installed = set(installed)
    acl_values, rule_values = sources_with_overrides(collector, installed)
    acls = [
        values
        for key, values in acl_values.items()
        if collector.acls[key].module in installed and values.get("model") in models
    ]
    rules = [
        values
        for key, values in rule_values.items()
        if collector.rules[key].module in installed and values.get("model") in models
    ]
    implied = collector.implications(installed)
    synthesized = ir_access_convert.synthesize(acls, rules, implied)
    off = {
        xmlid
        for module, xmlids in deactivations.items()
        if module in installed
        for xmlid in xmlids
    }
    present = {
        row["xmlid"]: dict(row)
        for row in rows
        if row["module"] in installed
        and row["model"] in models
        and row["xmlid"] not in off
    }
    for module in sorted(writes, key=lambda name: collector.modules[name].index):
        if module not in installed:
            continue
        for xmlid, changed in writes[module].items():
            if xmlid in present:
                present[xmlid].update(changed)
    present = list(present.values())
    closure = ir_access_convert.group_closures(
        implied, {row["group"] for row in [*synthesized, *present]}
    )
    by_model_old: dict[str, list] = defaultdict(list)
    by_model_new: dict[str, list] = defaultdict(list)
    for row in synthesized:
        by_model_old[row["model"]].append(row)
    for row in present:
        by_model_new[row["model"]].append(row)
    differences = []
    for model in sorted(set(by_model_old) | set(by_model_new)):
        old_rows, new_rows = by_model_old[model], by_model_new[model]
        groups = sorted({row["group"] for row in [*old_rows, *new_rows]})
        principals = {closure[g] for g in groups}
        principals |= {
            closure[a] | closure[b]
            for index, a in enumerate(groups)
            for b in groups[index + 1 :]
            if len((closure[a] | closure[b]) & ir_access_convert.EXCLUSIVE_GROUPS) <= 1
        }
        for principal in principals:
            for op in ir_access_convert.OPERATIONS:
                old = ir_access_convert.reach(old_rows, op, principal)
                new = ir_access_convert.reach(new_rows, op, principal)
                if old != new:
                    differences.append(
                        (
                            model,
                            op,
                            sorted(principal - {ir_access_convert.GROUP_EVERYONE}),
                            old.render(),
                            new.render(),
                        )
                    )
    return differences


def verify(
    collector: Collector, rows: list[dict], report, install_sets: dict[str, set[str]]
):
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor

    result = plan(collector, rows, report)
    deactivations = result["deactivations"]
    writes = result["writes"]
    rows = result["all_rows"]
    models_of: dict[str, set[str]] = defaultdict(set)
    for source in [
        *collector.acls.values(),
        *collector.rules.values(),
        *collector.overrides,
    ]:
        models_of[source.values.get("model")].add(source.module)
    for row in rows:
        models_of[row["model"]].add(row["module"])
    jobs = []
    for label, installed in install_sets.items():
        models = {model for model, modules in models_of.items() if modules & installed}
        jobs.append(
            (label, (collector, rows, deactivations, writes, sorted(installed), models))
        )
    report = {}
    with ProcessPoolExecutor(
        max_workers=16, mp_context=multiprocessing.get_context("fork")
    ) as pool:
        for (label, _job), differences in zip(
            jobs,
            pool.map(_verify_one, [job for _label, job in jobs], chunksize=8),
            strict=True,
        ):
            if differences:
                report[label] = differences
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite every ir.model.access CSV line and ir.rule record of the "
        "given addons roots into security/ir.access.csv with ir_access_convert."
    )
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--installed", type=Path, help="module names, one per line")
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="an access line or rule external id left out of the conversion "
        "(a line whose model is not in the tree yet)",
    )
    parser.add_argument(
        "--verify",
        choices=["full", "each", "file"],
        help="compare the rows present in an install (every module, or each module "
        "with its dependencies) against the conversion of that install's own lines "
        "and rules, principal by principal",
    )
    args = parser.parse_args()
    collector = Collector(args.roots)
    collector.run()
    for xmlid in args.skip:
        collector.acls.pop(xmlid, None)
        collector.rules.pop(xmlid, None)
    rows, report = collector.convert()
    summary = {
        "modules": len(collector.modules),
        "acl lines": len(collector.acls),
        "rules": len(collector.rules),
        "overrides": [(s.module, s.xmlid) for s in collector.overrides],
        "rows": len(rows),
        "kinds": Counter(f"{r['kind']}/{r['guard_scope']}" for r in rows),
        "conditional rows": sum(1 for r in rows if r["deactivated_by"]),
        "unplaced": report.unplaced,
        "collisions": report.collisions,
        "unmapped": report.unmapped,
        "problems": collector.problems,
    }
    if args.verify:
        sets = {"full": set(collector.modules)}
        if args.verify == "file":
            names = set(args.installed.read_text().split()) & set(collector.modules)
            sets = {str(args.installed): names}
        if args.verify == "each":
            sets |= {name: collector.closures[name] for name in collector.order}
        differences = verify(collector, rows, report, sets)
        summary["verify"] = {
            "install sets": len(sets),
            "differing": len(differences),
        }
        if args.json:
            args.json.with_suffix(".verify.json").write_text(
                json.dumps(differences, indent=1, default=list)
            )
    if args.apply:
        result = apply(collector, rows, report)
        summary["bridges"] = result["bridges"]
        summary["unplaced"] = result["unplaced"]
        summary["stats"] = result["stats"]
    else:
        result = plan(collector, rows, report)
        summary["bridges"] = result["bridges"]
        summary["unplaced"] = result["unplaced"]
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "summary": summary,
                    "rows": rows,
                    "xmlid_map": report.xmlid_map,
                    "sources": {
                        key: {
                            "module": s.module,
                            "entry": s.entry,
                            "noupdate": s.noupdate,
                        }
                        for key, s in [
                            *collector.acls.items(),
                            *collector.rules.items(),
                        ]
                    },
                },
                indent=1,
                default=list,
            )
        )
    for key, value in summary.items():
        if isinstance(value, list) and len(value) > 20:
            print(f"{key}: {len(value)}")
            for item in value[:20]:
                print(f"    {item}")
        else:
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
