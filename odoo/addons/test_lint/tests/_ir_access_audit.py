import argparse
import ast
import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

_CONVERT_PATH = (
    Path(__file__).resolve().parents[2] / "base" / "models" / "ir_access_convert.py"
)
_spec = importlib.util.spec_from_file_location("ir_access_convert", _CONVERT_PATH)
ir_access_convert = importlib.util.module_from_spec(_spec)
sys.modules["ir_access_convert"] = ir_access_convert
_spec.loader.exec_module(ir_access_convert)

PERMS = ("perm_read", "perm_write", "perm_create", "perm_unlink")
_MODEL_NAME_RE = re.compile(
    r"""^\s+_name\s*(?::[^=]+)?=\s*(["'])([\w.]+)\1""", re.MULTILINE
)
_FALSE_TEXT = {"0", "false", "off", "no", ""}


def qualify(module: str, xmlid: str | None) -> str | None:
    if not xmlid:
        return None
    return xmlid if "." in xmlid else f"{module}.{xmlid}"


def read_bool(node) -> bool:
    value = node.get("eval")
    if value is None:
        return (node.text or "").strip().lower() not in _FALSE_TEXT
    try:
        return bool(ast.literal_eval(value))
    except ValueError, SyntaxError:
        return value.strip() not in ("False", "0", "None")


def discover(roots: list[Path]) -> dict[str, tuple[Path, dict]]:
    modules: dict[str, tuple[Path, dict]] = {}
    for root in roots:
        for manifest in sorted(root.glob("*/__manifest__.py")):
            name = manifest.parent.name
            if name.startswith("test_") or name in modules:
                continue
            data = ast.literal_eval(manifest.read_text())
            modules[name] = (manifest.parent, data)
    return modules


def dependency_closure(modules) -> dict[str, set[str]]:
    closures: dict[str, set[str]] = {}

    def visit(name: str) -> set[str]:
        if name in closures:
            return closures[name]
        closures[name] = {name, "base"}
        for dep in modules.get(name, (None, {}))[1].get("depends", ()):
            closures[name] |= visit(dep)
        return closures[name]

    for name in modules:
        visit(name)
    return closures


def load_order(modules, closures) -> list[str]:
    return sorted(modules, key=lambda name: (len(closures[name]), name))


def model_names(modules) -> dict[str, str]:
    names: dict[str, str] = {}
    for path, _manifest in modules.values():
        for source in path.rglob("*.py"):
            if "tests" in source.parts:
                continue
            for match in _MODEL_NAME_RE.finditer(source.read_text(errors="replace")):
                model = match[2]
                names.setdefault(f"model_{model.replace('.', '_')}", model)
    return names


class GroupCommands(ast.NodeVisitor):
    def __init__(self, module: str):
        self.module = module
        self.commands: list[tuple[str, list[str]]] = []

    def refs(self, node) -> list[str]:
        return [
            qualify(self.module, sub.args[0].value)
            for sub in ast.walk(node)
            if isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id == "ref"
        ]

    def parse(self, expression: str) -> list[tuple[str, list[str]]]:
        tree = ast.parse(expression.strip(), mode="eval").body
        items = tree.elts if isinstance(tree, (ast.List, ast.Tuple)) else [tree]
        for item in items:
            if isinstance(item, ast.Tuple) and item.elts:
                code = ast.literal_eval(item.elts[0])
                verb = {4: "link", 3: "unlink", 6: "set", 5: "clear"}.get(code)
            elif isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
                verb = item.func.attr
            else:
                verb = None
            if verb is None:
                raise ValueError(f"unreadable command {ast.unparse(item)}")
            self.commands.append((verb, self.refs(item)))
        return self.commands


def apply_commands(current: set[str], commands) -> set[str]:
    for verb, refs in commands:
        if verb == "link":
            current |= set(refs)
        elif verb == "unlink":
            current -= set(refs)
        elif verb == "set":
            current = set(refs)
        elif verb == "clear":
            current = set()
    return current


class Collector:
    def __init__(self, roots: list[Path]):
        self.modules = discover(roots)
        self.closures = dependency_closure(self.modules)
        self.model_names = model_names(self.modules)
        self.acls: dict[str, dict] = {}
        self.rules: dict[str, dict] = {}
        self.implied: dict[str, set[str]] = defaultdict(set)
        self.problems: list[tuple[str, str]] = []
        self.overrides = Counter()
        self.files = Counter()

    def model(self, module: str, ref: str | None) -> str | None:
        if not ref:
            return None
        local = ref.rpartition(".")[2]
        if local in self.model_names:
            return self.model_names[local]
        self.problems.append((f"{module}:{ref}", "model external id not resolved"))
        return None

    def run(self) -> None:
        for module in load_order(self.modules, self.closures):
            path, manifest = self.modules[module]
            for name in manifest.get("data", ()):
                file = path / name
                if not file.exists():
                    continue
                if name.endswith(".csv") and file.name.startswith("ir.model.access"):
                    self.files["csv"] += 1
                    self.read_csv(module, file)
                elif name.endswith(".xml"):
                    self.read_xml(module, file)

    def read_csv(self, module: str, file: Path) -> None:
        with file.open(newline="", encoding="utf-8") as stream:
            for line in csv.DictReader(stream):
                if not line.get("id"):
                    continue
                xmlid = qualify(module, line["id"])
                model_ref = line.get("model_id:id") or line.get("model_id/id")
                group_ref = line.get("group_id:id") or line.get("group_id/id")
                record = self.acls.get(xmlid)
                if record is None:
                    record = self.acls[xmlid] = {
                        "xmlid": xmlid,
                        "module": xmlid.partition(".")[0],
                        "active": True,
                    }
                else:
                    self.overrides["ir.model.access"] += 1
                record["name"] = line.get("name") or record.get("name")
                record["model"] = self.model(module, model_ref)
                record["group"] = qualify(module, group_ref) if group_ref else None
                for perm in PERMS:
                    record[perm] = (line.get(perm) or "0").strip() not in ("0", "")

    def read_xml(self, module: str, file: Path) -> None:
        try:
            tree = etree.parse(str(file))
        except etree.XMLSyntaxError as error:
            self.problems.append((str(file), f"unparsable XML: {error}"))
            return
        for record in tree.iter("record"):
            kind = record.get("model")
            if kind not in ("ir.model.access", "ir.rule", "res.groups"):
                continue
            xmlid = qualify(module, record.get("id"))
            if xmlid is None:
                continue
            try:
                getattr(self, "xml_" + kind.replace(".", "_"))(module, xmlid, record)
            except (ValueError, SyntaxError, AttributeError, IndexError) as error:
                self.problems.append((xmlid, f"unreadable {kind} record: {error}"))

    def fields(self, record):
        return {node.get("name"): node for node in record.findall("field")}

    def xml_model(self, module, node) -> str | None:
        if node.get("ref"):
            return self.model(module, node.get("ref"))
        if node.get("search"):
            for leaf in ast.literal_eval(node.get("search")):
                if leaf[0] == "model" and leaf[1] == "=":
                    return leaf[2]
        return None

    def xml_ir_model_access(self, module, xmlid, record) -> None:
        fields = self.fields(record)
        acl = self.acls.get(xmlid)
        if acl is None:
            acl = self.acls[xmlid] = {
                "xmlid": xmlid,
                "module": xmlid.partition(".")[0],
                "active": True,
                **dict.fromkeys(PERMS, False),
                "group": None,
            }
        else:
            self.overrides["ir.model.access"] += 1
        if "name" in fields:
            acl["name"] = fields["name"].text
        if "model_id" in fields:
            acl["model"] = self.xml_model(module, fields["model_id"])
        if "group_id" in fields:
            acl["group"] = qualify(module, fields["group_id"].get("ref"))
        for perm in PERMS:
            if perm in fields:
                acl[perm] = read_bool(fields[perm])
        if "active" in fields:
            acl["active"] = read_bool(fields["active"])

    def xml_ir_rule(self, module, xmlid, record) -> None:
        fields = self.fields(record)
        rule = self.rules.get(xmlid)
        if rule is None:
            rule = self.rules[xmlid] = {
                "xmlid": xmlid,
                "module": xmlid.partition(".")[0],
                "active": True,
                "groups": [],
                **dict.fromkeys(PERMS),
            }
        else:
            self.overrides["ir.rule"] += 1
        if "name" in fields:
            rule["name"] = fields["name"].text
        if "model_id" in fields:
            rule["model"] = self.xml_model(module, fields["model_id"])
        if "domain_force" in fields:
            rule["domain_force"] = fields["domain_force"].text
        if "groups" in fields:
            commands = GroupCommands(module).parse(fields["groups"].get("eval") or "[]")
            rule["groups"] = sorted(apply_commands(set(rule["groups"]), commands))
        for perm in PERMS:
            if perm in fields:
                rule[perm] = read_bool(fields[perm])
        if "active" in fields:
            rule["active"] = read_bool(fields["active"])
        if "composition" in fields:
            rule["composition"] = (fields["composition"].text or "").strip()

    def xml_res_groups(self, module, xmlid, record) -> None:
        fields = self.fields(record)
        self.implied.setdefault(xmlid, set())
        if (node := fields.get("implied_ids")) is not None and node.get("eval"):
            commands = GroupCommands(module).parse(node.get("eval"))
            self.implied[xmlid] = apply_commands(self.implied[xmlid], commands)
        if (node := fields.get("implied_by_ids")) is not None and node.get("eval"):
            for verb, refs in GroupCommands(module).parse(node.get("eval")):
                for ref in refs:
                    if verb == "link":
                        self.implied[ref].add(xmlid)
                    elif verb == "unlink":
                        self.implied[ref].discard(xmlid)


def table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [
        min(max(len(str(cell)) for cell in column), 70)
        for column in zip(headers, *rows, strict=True)
    ]
    lines = [" | ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))]
    lines.append("-+-".join("-" * w for w in widths))
    lines.extend(
        " | ".join(str(c).ljust(w) for c, w in zip(row, widths, strict=True))
        for row in rows
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert every ir.model.access line and ir.rule record of the "
        "given addons roots with ir_access_convert and print the report."
    )
    parser.add_argument("roots", nargs="+", type=Path)
    args = parser.parse_args()

    collector = Collector(args.roots)
    collector.run()
    acls = list(collector.acls.values())
    rules = list(collector.rules.values())
    rows, report = ir_access_convert.convert(
        acls, rules, collector.implied, module_deps=collector.closures
    )
    implied = {g: sorted(t) for g, t in collector.implied.items()}
    out = []
    kinds = Counter((row["kind"], row["guard_scope"]) for row in rows)
    mono_models = {entry["model"] for entry in report.monotonicity}
    mono_pairs = {(e["model"], e["alone"], e["added"]) for e in report.monotonicity}
    everyone = {k for k in mono_pairs if k[1] == ir_access_convert.GROUP_EVERYONE}
    external = {
        (e["model"], e["alone"], e["added"])
        for e in report.monotonicity
        if {"base.group_portal", "base.group_public"} & set(e["roles"])
    }
    restriction = {
        (e["model"], e["alone"], e["added"])
        for e in report.monotonicity
        if not e["added_has_access"]
    }
    directions = Counter(change["direction"] for change in report.changes)
    out.append("# ir.access conversion audit")
    out.append(f"modules scanned: {len(collector.modules)} (test_* excluded)")
    out.append(f"access CSV files: {collector.files['csv']}")
    out.append(
        f"ir.model.access lines: {len(acls)} "
        f"(active {sum(1 for a in acls if a.get('active', True))})"
    )
    out.append(
        f"ir.rule records: {len(rules)} "
        f"(active {sum(1 for r in rules if r.get('active', True))}, "
        f"global {sum(1 for r in rules if not r.get('groups'))}, "
        f"restrict {sum(1 for r in rules if r.get('composition') == 'restrict')})"
    )
    out.append(f"override records merged: {dict(collector.overrides)}")
    out.append(f"res.groups with implications: {sum(1 for t in implied.values() if t)}")
    out.append(f"ir.access rows produced: {len(rows)}")
    for (kind, scope), count in sorted(kinds.items(), key=str):
        out.append(f"  {kind}{f' ({scope})' if scope else ''}: {count}")
    out.append(
        f"(a) monotonicity: {len(mono_pairs)} (model, group alone, group added) pairs "
        f"on {len(mono_models)} models, {len(everyone)} of them with "
        f"'{ir_access_convert.GROUP_EVERYONE}' alone (a group-less access line)"
    )
    out.append(
        f"    of which {len(external)} put a portal or public role beside the first "
        f"group, {len(mono_pairs - external)} are internal users; "
        f"{len(restriction)} add a group with no access of its own to the model "
        f"(a restriction group: its rule was only ever a restriction), "
        f"{len(restriction - external)} of them internal"
    )
    out.append(
        f"(a) every principal whose reach changes: {len(report.changes)} "
        f"{dict(directions)}"
    )
    out.append(
        f"(b) access lines that see all beside other groups' rules: "
        f"{len(report.see_all_beside_rules)}"
    )
    out.append(
        f"(b) dead rules: {sum(1 for d in report.dead_rules if d['whole'])} whole, "
        f"{sum(1 for d in report.dead_rules if not d['whole'])} on some operations"
    )
    out.append(
        f"(b) mode-blind rules (no perm_*, converted to crud): "
        f"{len(report.mode_blind_rules)}"
    )
    out.append(
        f"(c) domains that test the user's groups: {len(report.group_test_domains)}"
    )
    out.append(
        f"(c) not mapped by the converter: {len(report.unmapped)}; "
        f"by the audit's reader: {len(collector.problems)}"
    )

    out.append(
        "\n## (a) Monotonicity: holding both groups saw fewer records than "
        "the first alone; after conversion they see what the first sees"
    )
    out.append(
        table(
            [
                [
                    e["model"],
                    e["alone"],
                    e["added"],
                    e["operation"],
                    ",".join(r.removeprefix("base.group_") for r in e["roles"]) or "-",
                    "no" if not e["added_has_access"] else "yes",
                    e["old_both"],
                    e["new_both"],
                ]
                for e in report.monotonicity
            ],
            [
                "model",
                "group alone (sees all)",
                "group added",
                "ops",
                "role",
                "added has access",
                "old: both groups",
                "new: both groups",
            ],
        )
    )

    for direction in ("narrows", "guards differ", "differs", "widens"):
        selected = [c for c in report.changes if c["direction"] == direction]
        out.append(f"\n## (a) Principals whose reach {direction} ({len(selected)})")
        out.append(
            table(
                [
                    [c["model"], c["principal"], c["operation"], c["old"], c["new"]]
                    for c in selected
                ],
                ["model", "principal", "ops", "old", "new"],
            )
        )

    out.append(
        f"\n## (b) Access lines that see all beside other groups' rules "
        f"({len(report.see_all_beside_rules)})"
    )
    out.append(
        table(
            [
                [
                    e["model"],
                    e["acl"],
                    e["group"],
                    e["operation"],
                    ", ".join(e["rule_groups"]),
                ]
                for e in report.see_all_beside_rules
            ],
            ["model", "access line", "group", "ops", "groups with rules"],
        )
    )
    out.append(
        f"\n## (b) Dead rules: operations no access line gives their group "
        f"({len(report.dead_rules)})"
    )
    out.append(
        table(
            [
                [
                    d["model"],
                    d["rule"],
                    d["group"],
                    d["operation"],
                    "whole rule" if d["whole"] else "partly",
                ]
                for d in report.dead_rules
            ],
            ["model", "rule", "group", "dead ops", "extent"],
        )
    )
    out.append(f"\n## (b) Mode-blind rules ({len(report.mode_blind_rules)})")
    out.extend(report.mode_blind_rules)
    out.append(
        f"\n## (c) Domains that test the user's groups "
        f"({len(report.group_test_domains)})"
    )
    out.extend(report.group_test_domains)
    out.append(f"\n## (c) Not mapped ({len(report.unmapped)})")
    out.extend(f"{u['source']}: {u['reason']}" for u in report.unmapped)
    out.append(f"\n## (c) Unreadable sources ({len(collector.problems)})")
    out.extend(f"{source}: {reason}" for source, reason in collector.problems)
    renamed = {old: new for old, new in report.xmlid_map.items() if new != [old]}
    out.append(
        f"\n## External ids: {len(report.xmlid_map)} old ids, "
        f"{len(renamed)} not kept as is"
    )
    out.extend(f"{old} -> {', '.join(new)}" for old, new in renamed.items())
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
