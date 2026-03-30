from __future__ import annotations

from dataclasses import dataclass
import csv
from io import StringIO
from pathlib import Path
import hashlib
import json
import re
from typing import Any
from xml.etree.ElementTree import Comment, Element, SubElement, fromstring, indent, tostring

from ..config import get_settings


PY_CUSTOM_BLOCK_RE = re.compile(
    r"(?ms)^# forge:custom begin (?P<name>[a-zA-Z0-9_.:-]+)\n(?P<body>.*?)^# forge:custom end (?P=name)\n?"
)
XML_CUSTOM_BLOCK_RE = re.compile(
    r"(?ms)<!-- forge:custom begin (?P<name>[a-zA-Z0-9_.:-]+) -->\n?(?P<body>.*?)<!-- forge:custom end (?P=name) -->"
)
SCALAR_FIELD_TYPES = {
    "char": "Char",
    "text": "Text",
    "integer": "Integer",
    "float": "Float",
    "boolean": "Boolean",
    "date": "Date",
    "datetime": "Datetime",
}
NUMERIC_FIELD_TYPES = {"integer", "float"}
RELATIONAL_FIELD_TYPES = {"many2one", "one2many", "many2many"}


@dataclass
class GeneratedFile:
    path: str
    content: str
    artifact_type: str
    content_hash: str
    model_hash: str


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _python_block(block_id: str, body: str) -> str:
    return (
        f"# forge:generated begin {block_id}\n"
        f"{body.rstrip()}\n"
        f"# forge:generated end {block_id}\n\n"
        "# forge:custom begin extra\n"
        "# forge:custom end extra\n"
    )


def _xml_document(block_id: str, nodes: list[Element]) -> str:
    root = Element("odoo")
    root.append(Comment(f" forge:generated begin {block_id} "))
    for node in nodes:
        root.append(node)
    root.append(Comment(f" forge:generated end {block_id} "))
    root.append(Comment(" forge:custom begin extra "))
    root.append(Comment(" forge:custom end extra "))
    indent(root, space="    ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + tostring(root, encoding="unicode") + "\n"


def _parse_custom_blocks(content: str, path: str) -> dict[str, str]:
    if path.endswith(".py"):
        return {match.group("name"): match.group("body") for match in PY_CUSTOM_BLOCK_RE.finditer(content)}
    if path.endswith(".xml"):
        return {match.group("name"): match.group("body") for match in XML_CUSTOM_BLOCK_RE.finditer(content)}
    return {}


def _merge_custom_blocks(content: str, existing_content: str | None, path: str) -> str:
    if not existing_content:
        return content
    custom_blocks = _parse_custom_blocks(existing_content, path)
    if not custom_blocks:
        return content
    if path.endswith(".py"):
        for name, body in custom_blocks.items():
            pattern = re.compile(
                rf"(?ms)^[ \t]*# forge:custom begin {re.escape(name)}\n^[ \t]*# forge:custom end {re.escape(name)}\n?"
            )
            replacement = (
                f"# forge:custom begin {name}\n"
                f"{body}"
                f"# forge:custom end {name}\n"
            )
            content = pattern.sub(replacement, content)
    elif path.endswith(".xml"):
        for name, body in custom_blocks.items():
            pattern = re.compile(
                rf"(?ms)^[ \t]*<!-- forge:custom begin {re.escape(name)} -->\n^[ \t]*<!-- forge:custom end {re.escape(name)} -->"
            )
            replacement = (
                f"    <!-- forge:custom begin {name} -->\n"
                f"{body}"
                f"    <!-- forge:custom end {name} -->"
            )
            content = pattern.sub(replacement, content)
    return content


def _literal_default(field_row: dict[str, Any]) -> str | None:
    raw_value = field_row.get("default_value")
    if raw_value in (None, ""):
        return None
    if field_row["field_type"] == "boolean":
        return "True" if str(raw_value).strip().lower() in {"1", "true", "yes"} else "False"
    if field_row["field_type"] == "integer":
        try:
            return str(int(raw_value))
        except ValueError:
            return repr(str(raw_value))
    if field_row["field_type"] == "float":
        try:
            return str(float(raw_value))
        except ValueError:
            return repr(str(raw_value))
    return repr(str(raw_value))


def _render_field_line(field_row: dict[str, Any]) -> str:
    kwargs = [f"string={field_row['string']!r}"]
    if field_row.get("required"):
        kwargs.append("required=True")
    if field_row.get("index"):
        kwargs.append("index=True")
    default_literal = _literal_default(field_row)
    if default_literal is not None:
        kwargs.append(f"default={default_literal}")

    field_type = field_row["field_type"]
    if field_type in SCALAR_FIELD_TYPES:
        return f"    {field_row['name']} = fields.{SCALAR_FIELD_TYPES[field_type]}({', '.join(kwargs)})"
    if field_type == "many2one":
        args = [repr(field_row["relation_model"])] + kwargs
        return f"    {field_row['name']} = fields.Many2one({', '.join(args)})"
    if field_type == "one2many":
        args = [
            repr(field_row["relation_model"]),
            repr(field_row["relation_field"]),
        ] + kwargs
        return f"    {field_row['name']} = fields.One2many({', '.join(args)})"
    if field_type == "many2many":
        args = [repr(field_row["relation_model"])] + kwargs
        return f"    {field_row['name']} = fields.Many2many({', '.join(args)})"
    return f"    # Unsupported field {field_row['name']}"


def _render_model_file(model_row: dict[str, Any]) -> str:
    body_lines = ["from odoo import fields, models", "", ""]
    body_lines.append(f"class {model_row['class_name']}(models.Model):")
    body_lines.append(f"    _name = {model_row['technical_name']!r}")
    body_lines.append(f"    _description = {model_row['name']!r}")
    body_lines.append("")
    if model_row["fields"]:
        for field_row in model_row["fields"]:
            body_lines.append(_render_field_line(field_row))
    else:
        body_lines.append("    pass")
    body = "\n".join(body_lines).rstrip() + "\n"
    return _python_block(f"model:{model_row['technical_name']}", body)


def _render_models_init(model_rows: list[dict[str, Any]]) -> str:
    imports = [f"from . import {Path(model_row['file_name']).stem}" for model_row in model_rows]
    body = "\n".join(imports) + ("\n" if imports else "")
    return _python_block("models.__init__", body)


def _render_root_init() -> str:
    return _python_block("__init__", "from . import models\n")


def _render_manifest(representation: dict[str, Any], data_files: list[str]) -> str:
    depends = list(dict.fromkeys(representation["module"]["depends_list"]))
    if "base" not in depends:
        depends.insert(0, "base")
    if representation.get("automations_present") and "base_automation" not in depends:
        depends.append("base_automation")
    lines = [
        "{",
        f"    'name': {representation['module']['name']!r},",
        f"    'version': {representation['module'].get('version')!r},",
        "    'license': 'LGPL-3',",
        "    'installable': True,",
        "    'application': False,",
        f"    'depends': {depends!r},",
        f"    'data': {data_files!r},",
        "}",
    ]
    return _python_block("__manifest__", "\n".join(lines) + "\n")


def _field_name_for_view(field_row: dict[str, Any]) -> str:
    return field_row["name"]


def _default_view_arch(view_row: dict[str, Any], model_row: dict[str, Any]) -> str:
    view_type = view_row["view_type"]
    fields = model_row["fields"]
    field_names = [_field_name_for_view(field_row) for field_row in fields]
    if view_type in {"tree", "list"}:
        root = Element(view_type)
        for field_name in field_names[:8]:
            SubElement(root, "field", {"name": field_name})
    elif view_type == "form":
        root = Element("form")
        sheet = SubElement(root, "sheet")
        group = SubElement(sheet, "group")
        for field_name in field_names[:12]:
            SubElement(group, "field", {"name": field_name})
    elif view_type == "search":
        root = Element("search")
        for field_name in field_names[:8]:
            SubElement(root, "field", {"name": field_name})
    elif view_type == "kanban":
        root = Element("kanban")
        templates = SubElement(root, "templates")
        template = SubElement(templates, "t", {"t-name": "card"})
        for field_name in field_names[:5]:
            SubElement(template, "field", {"name": field_name})
    elif view_type == "pivot":
        root = Element("pivot")
        for field_row in fields:
            attrs = {"name": field_row["name"]}
            if field_row["field_type"] in NUMERIC_FIELD_TYPES:
                attrs["type"] = "measure"
            SubElement(root, "field", attrs)
    else:
        root = Element("graph")
        for field_row in fields:
            attrs = {"name": field_row["name"]}
            if field_row["field_type"] in NUMERIC_FIELD_TYPES:
                attrs["type"] = "measure"
            SubElement(root, "field", attrs)
    indent(root, space="        ")
    return tostring(root, encoding="unicode")


def _render_view_record(view_row: dict[str, Any], model_row: dict[str, Any]) -> Element:
    record = Element("record", {"id": view_row["xmlid"], "model": "ir.ui.view"})
    SubElement(record, "field", {"name": "name"}).text = view_row["name"]
    SubElement(record, "field", {"name": "model"}).text = model_row["technical_name"]
    SubElement(record, "field", {"name": "priority"}).text = str(view_row.get("priority", 16))
    arch_field = SubElement(record, "field", {"name": "arch", "type": "xml"})
    arch_xml = view_row.get("arch_base") or _default_view_arch(view_row, model_row)
    arch_field.append(fromstring(arch_xml))
    return record


def _render_groups_xml(representation: dict[str, Any]) -> str:
    nodes: list[Element] = []
    for group_row in representation["groups"]:
        record = Element("record", {"id": group_row["xmlid"], "model": "res.groups"})
        SubElement(record, "field", {"name": "name"}).text = group_row["name"]
        implied_ids = group_row.get("implied_ids") or []
        if implied_ids:
            refs = []
            for implied_id in implied_ids:
                target = next(
                    (candidate for candidate in representation["groups"] if candidate["id"] == implied_id),
                    None,
                )
                if target:
                    refs.append(f"ref('{representation['module']['technical_name']}.{target['xmlid']}')")
            if refs:
                SubElement(record, "field", {"name": "implied_ids", "eval": f"[(6, 0, [{', '.join(refs)}])]"})
        nodes.append(record)
    return _xml_document("groups", nodes)


def _render_actions_xml(representation: dict[str, Any]) -> str:
    nodes: list[Element] = []
    for action_row in representation["actions"]:
        model_row = representation["model_lookup"].get(action_row["model_id"])
        if not model_row:
            continue
        record = Element("record", {"id": action_row["xmlid"], "model": "ir.actions.act_window"})
        SubElement(record, "field", {"name": "name"}).text = action_row["name"]
        SubElement(record, "field", {"name": "res_model"}).text = model_row["technical_name"]
        SubElement(record, "field", {"name": "view_mode"}).text = action_row.get("view_mode") or "list,form"
        SubElement(record, "field", {"name": "domain"}).text = action_row.get("domain") or "[]"
        SubElement(record, "field", {"name": "context"}).text = action_row.get("context") or "{}"
        nodes.append(record)
    return _xml_document("actions", nodes)


def _render_menus_xml(representation: dict[str, Any]) -> str:
    nodes: list[Element] = []
    menu_lookup = {menu_row["id"]: menu_row for menu_row in representation["menus"]}
    action_lookup = {action_row["id"]: action_row for action_row in representation["actions"]}
    for menu_row in representation["menus"]:
        record = Element("record", {"id": menu_row["xmlid"], "model": "ir.ui.menu"})
        SubElement(record, "field", {"name": "name"}).text = menu_row["name"]
        SubElement(record, "field", {"name": "sequence"}).text = str(menu_row.get("sequence", 10))
        if menu_row.get("web_icon"):
            SubElement(record, "field", {"name": "web_icon"}).text = menu_row["web_icon"]
        if menu_row.get("parent_id"):
            parent_row = menu_lookup.get(menu_row["parent_id"])
            if parent_row:
                SubElement(
                    record,
                    "field",
                    {
                        "name": "parent_id",
                        "ref": f"{representation['module']['technical_name']}.{parent_row['xmlid']}",
                    },
                )
        if menu_row.get("action_id"):
            action_row = action_lookup.get(menu_row["action_id"])
            if action_row:
                SubElement(
                    record,
                    "field",
                    {
                        "name": "action",
                        "ref": f"{representation['module']['technical_name']}.{action_row['xmlid']}",
                    },
                )
        nodes.append(record)
    return _xml_document("menus", nodes)


def _render_automations_xml(representation: dict[str, Any]) -> str:
    nodes: list[Element] = []
    for model_row in representation["models"]:
        for automation_row in model_row["automations"]:
            if automation_row["trigger"] == "on_time":
                nodes.append(
                    Comment(
                        f" forge warning: automation {automation_row['name']} requires manual trigger date metadata "
                    )
                )
                continue
            action_xmlid = f"{xml_token(automation_row['name'])}_server"
            automation_xmlid = f"automation_{xml_token(automation_row['name'])}"
            action_record = Element("record", {"id": action_xmlid, "model": "ir.actions.server"})
            SubElement(action_record, "field", {"name": "name"}).text = automation_row["name"]
            SubElement(
                action_record,
                "field",
                {"name": "model_id", "ref": f"model_{model_row['technical_name'].replace('.', '_')}"},
            )
            SubElement(action_record, "field", {"name": "state"}).text = "code"
            SubElement(action_record, "field", {"name": "code"}).text = automation_row.get("code") or ""
            nodes.append(action_record)

            automation_record = Element("record", {"id": automation_xmlid, "model": "base.automation"})
            SubElement(automation_record, "field", {"name": "name"}).text = automation_row["name"]
            SubElement(
                automation_record,
                "field",
                {"name": "model_id", "ref": f"model_{model_row['technical_name'].replace('.', '_')}"},
            )
            SubElement(automation_record, "field", {"name": "trigger"}).text = automation_row["trigger"]
            SubElement(automation_record, "field", {"name": "filter_domain"}).text = automation_row.get("filter_domain") or "[]"
            SubElement(
                automation_record,
                "field",
                {"name": "action_server_ids", "eval": f"[(4, ref('{representation['module']['technical_name']}.{action_xmlid}'))]"},
            )
            nodes.append(automation_record)
    return _xml_document("automations", nodes)


def _render_access_csv(representation: dict[str, Any]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["id", "name", "model_id:id", "group_id:id", "perm_read", "perm_write", "perm_create", "perm_unlink"]
    )
    group_lookup = {group_row["id"]: group_row for group_row in representation["groups"]}
    for model_row in representation["models"]:
        model_xmlid = f"model_{model_row['technical_name'].replace('.', '_')}"
        for access_row in model_row["accesses"]:
            group_row = group_lookup.get(access_row.get("group_id"))
            group_ref = (
                f"{representation['module']['technical_name']}.{group_row['xmlid']}" if group_row else ""
            )
            writer.writerow(
                [
                    f"access_{xml_token(access_row['name'])}",
                    access_row["name"],
                    model_xmlid,
                    group_ref,
                    "1" if access_row.get("perm_read") else "0",
                    "1" if access_row.get("perm_write") else "0",
                    "1" if access_row.get("perm_create") else "0",
                    "1" if access_row.get("perm_unlink") else "0",
                ]
            )
    return buffer.getvalue()


def _make_generated_file(path: str, content: str, artifact_type: str, source: Any) -> GeneratedFile:
    model_hash = _hash_text(_stable_json(source))
    content_hash = _hash_text(content)
    return GeneratedFile(
        path=path,
        content=content,
        artifact_type=artifact_type,
        content_hash=content_hash,
        model_hash=model_hash,
    )


def generate_module_files(representation: dict[str, Any]) -> list[GeneratedFile]:
    files: list[GeneratedFile] = []
    files.append(
        _make_generated_file(
            "__init__.py",
            _render_root_init(),
            "manifest",
            {"type": "__init__", "module": representation["module"]["technical_name"]},
        )
    )
    model_files: list[GeneratedFile] = []
    for model_row in representation["models"]:
        model_files.append(
            _make_generated_file(
                f"models/{model_row['file_name']}",
                _render_model_file(model_row),
                "model",
                {
                    "model": model_row["technical_name"],
                    "fields": model_row["fields"],
                },
            )
        )
    files.extend(model_files)
    files.append(
        _make_generated_file(
            "models/__init__.py",
            _render_models_init(representation["models"]),
            "model",
            {"models": [model_row["technical_name"] for model_row in representation["models"]]},
        )
    )

    data_files: list[str] = []
    if representation["groups"]:
        path = "security/groups.xml"
        files.append(
            _make_generated_file(path, _render_groups_xml(representation), "security", representation["groups"])
        )
        data_files.append(path)
    path = "security/ir.model.access.csv"
    files.append(
        _make_generated_file(
            path,
            _render_access_csv(representation),
            "security",
            {
                "models": [model_row["technical_name"] for model_row in representation["models"]],
                "accesses": [model_row["accesses"] for model_row in representation["models"]],
                "groups": representation["groups"],
            },
        )
    )
    data_files.append(path)

    for model_row in representation["models"]:
        for view_row in model_row["views"]:
            view_payload = {
                **view_row,
                "xmlid": f"view_{xml_token(model_row['technical_name'])}_{xml_token(view_row['name'])}",
            }
            path = f"views/{xml_token(model_row['technical_name'])}_{xml_token(view_row['name'])}.xml"
            files.append(
                _make_generated_file(
                    path,
                    _xml_document(
                        view_payload["xmlid"],
                        [_render_view_record(view_payload, model_row)],
                    ),
                    "view",
                    {"model": model_row["technical_name"], "view": view_payload},
                )
            )
            data_files.append(path)

    if representation["actions"]:
        path = "views/actions.xml"
        files.append(
            _make_generated_file(path, _render_actions_xml(representation), "view", representation["actions"])
        )
        data_files.append(path)
    if representation["menus"]:
        path = "views/menus.xml"
        files.append(
            _make_generated_file(path, _render_menus_xml(representation), "view", representation["menus"])
        )
        data_files.append(path)
    automations_present = any(model_row["automations"] for model_row in representation["models"])
    representation["automations_present"] = automations_present
    if automations_present:
        path = "data/automations.xml"
        files.append(
            _make_generated_file(
                path,
                _render_automations_xml(representation),
                "automation",
                [model_row["automations"] for model_row in representation["models"]],
            )
        )
        data_files.append(path)

    files.append(
        _make_generated_file(
            "__manifest__.py",
            _render_manifest(representation, data_files),
            "manifest",
            {"module": representation["module"], "data_files": data_files},
        )
    )
    return files


def detect_export_conflicts(
    representation: dict[str, Any],
    generated_files: list[GeneratedFile],
    previous_artifacts: dict[str, dict[str, Any]],
) -> list[str]:
    settings = get_settings()
    module_root = settings.module_output_dir(
        representation["app"]["technical_name"],
        representation["module"]["technical_name"],
    )
    conflicts: list[str] = []
    current_paths = {generated.path for generated in generated_files}
    for generated in generated_files:
        target_path = module_root / generated.path
        previous = previous_artifacts.get(generated.path)
        if target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8")
            existing_hash = _hash_text(existing_content)
            if previous is None:
                conflicts.append(f"{generated.path}: unmanaged existing file")
                continue
            if existing_hash != previous["content_hash"] and generated.model_hash == previous["model_hash"]:
                conflicts.append(f"{generated.path}: developer edits conflict with unchanged model")
    for path, previous in previous_artifacts.items():
        if path in current_paths:
            continue
        target_path = module_root / path
        if target_path.exists():
            existing_hash = _hash_text(target_path.read_text(encoding="utf-8"))
            if existing_hash != previous["content_hash"]:
                conflicts.append(f"{path}: removed file was edited manually")
    return conflicts


def write_generated_files(
    representation: dict[str, Any],
    generated_files: list[GeneratedFile],
    previous_artifacts: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    settings = get_settings()
    module_root = settings.module_output_dir(
        representation["app"]["technical_name"],
        representation["module"]["technical_name"],
    )
    module_root.mkdir(parents=True, exist_ok=True)
    applied: list[str] = []
    conflicts: list[str] = []
    current_paths = {generated.path for generated in generated_files}
    for generated in generated_files:
        target_path = module_root / generated.path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        previous = previous_artifacts.get(generated.path)
        existing_content = target_path.read_text(encoding="utf-8") if target_path.exists() else None
        if existing_content is not None:
            existing_hash = _hash_text(existing_content)
            if previous is None:
                conflicts.append(f"{generated.path}: unmanaged existing file")
                continue
            if existing_hash != previous["content_hash"] and generated.model_hash == previous["model_hash"]:
                conflicts.append(f"{generated.path}: developer edits conflict with unchanged model")
                continue
            merged_content = _merge_custom_blocks(generated.content, existing_content, generated.path)
            if _hash_text(merged_content) == existing_hash:
                continue
            target_path.write_text(merged_content, encoding="utf-8")
            applied.append(generated.path)
        else:
            target_path.write_text(generated.content, encoding="utf-8")
            applied.append(generated.path)
    for path, previous in previous_artifacts.items():
        if path in current_paths:
            continue
        target_path = module_root / path
        if not target_path.exists():
            continue
        existing_hash = _hash_text(target_path.read_text(encoding="utf-8"))
        if existing_hash != previous["content_hash"]:
            conflicts.append(f"{path}: removed file was edited manually")
            continue
        target_path.unlink()
        applied.append(path)
    return applied, conflicts
