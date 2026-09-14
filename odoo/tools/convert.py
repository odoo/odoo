__all__ = [
    "convert_csv_import",
    "convert_file",
    "convert_sql_import",
    "convert_xml_import",
    "reload_records",
]
import base64
import csv
import functools
import io
import logging
import pprint
import re
import subprocess
import warnings
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Literal

from dateutil.relativedelta import relativedelta
from lxml import builder, etree

try:
    import jingtrang
except ImportError:
    jingtrang = None

from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.text import split_refs, str2bool

if TYPE_CHECKING:
    from odoo.api import Environment
    from odoo.models import BaseModel
    from odoo.orm.primitives import CommandValue

from .config import config
from .files import file_open, file_path
from .misc import SKIPPED_ELEMENT_TYPES
from .safe_eval import _UNSAFE_ATTRIBUTES, pytz, safe_eval, time

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_ABORT_RECORD = object()
_SKIP_FIELD = object()

type ConvertMode = Literal["init", "update"]
type IdRef = dict[str, int | Literal[False]]


class ParseError(Exception): ...


def _check_model_name(f_model: str | None) -> str:
    if not f_model:
        raise ValueError('Define an attribute model="..." in your .XML file!')
    return f_model


def _prepare_eval_context(
    self: Any, env: Environment, model_str: str | None
) -> dict[str, Any]:
    from odoo import fields, release

    context = {
        "Command": fields.Command,
        "time": time,
        "DateTime": datetime,
        "datetime": datetime,
        "timedelta": timedelta,
        "relativedelta": relativedelta,
        "version": release.major_version,
        "ref": self.id_get,
        "pytz": pytz,
    }
    if model_str:
        context["obj"] = env[model_str].browse
    return context


def _fix_multiple_roots(node: etree._Element) -> None:
    real_nodes = [x for x in node if not isinstance(x, SKIPPED_ELEMENT_TYPES)]
    if len(real_nodes) > 1:
        data_node = etree.Element("data")
        for child in node:
            data_node.append(child)
        node.append(data_node)


def _substitute_xml_ids(self: Any, s: str) -> str:
    def repl(m: re.Match) -> str:
        if m.group(0) == "%%":
            return "%"
        rec_id = m.group(1)
        xid = self.normalize_xml_id(rec_id)
        if (record_id := self.idref.get(xid)) is None:
            record_id = self.idref[xid] = self.id_get(xid)
        return str(record_id)

    return re.sub(r"%%|%\((.*?)\)[ds]", repl, s)


def _eval_xml_search(
    self: Any,
    node: etree._Element,
    env: Environment,
    f_model: str | None,
    f_search: str,
) -> Any:
    f_use = node.get("use", "id")
    f_name = node.get("name")
    f_model = _check_model_name(f_model)
    context = _prepare_eval_context(self, env, f_model)
    q = safe_eval(f_search, context)
    records = env[f_model].search(q)
    ids = records.ids
    if f_use != "id":
        ids = [x[f_use] for x in records.read([f_use])]
    _fields = env[f_model]._fields
    _debug.logic(
        "convert.value.search",
        module=self.module,
        model=f_model,
        field=f_name,
        use=f_use,
        matches=len(ids),
    )
    if (f_name in _fields) and _fields[f_name].type == "many2many":
        return ids
    if not ids:
        return False
    f_val = ids[0]
    return f_val[0] if isinstance(f_val, tuple) else f_val


def _eval_xml_markup(self: Any, node: etree._Element, t: str) -> str:
    if t == "xml":
        _fix_multiple_roots(node)
        return '<?xml version="1.0"?>\n' + _substitute_xml_ids(
            self, "".join(etree.tostring(n, encoding="unicode") for n in node)
        )
    return _substitute_xml_ids(
        self,
        "".join(etree.tostring(n, method="html", encoding="unicode") for n in node),
    )


def _eval_xml_literal(self: Any, node: etree._Element, env: Environment, t: str) -> Any:
    if node.get("file"):
        if t == "base64":
            with file_open(node.get("file"), "rb", env=env) as f:
                return base64.b64encode(f.read())

        with file_open(node.get("file"), env=env) as f:
            data = f.read()
    else:
        data = node.text or ""

    match t:
        case "file":
            path = data.strip()
            try:
                file_path(str(Path(self.module, path)))
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"No such file or directory: {path!r} in {self.module}"
                ) from None
            return "%s,%s" % (self.module, path)
        case "char":
            return data
        case "int":
            d = data.strip()
            return None if d == "None" else int(d)
        case "float":
            return float(data.strip())
        case "list":
            return [_eval_xml(self, n, env) for n in node.iterchildren("value")]
        case "tuple":
            return tuple(_eval_xml(self, n, env) for n in node.iterchildren("value"))
        case "base64":
            msg = "base64 type is only compatible with file data"
            raise ValueError(msg)
        case t:
            raise ValueError(f"Unknown type {t!r}")


def _eval_xml_field(self: Any, node: etree._Element, env: Environment) -> Any:
    t = node.get("type", "char")
    f_model = node.get("model")
    if f_search := node.get("search"):
        return _eval_xml_search(self, node, env, f_model, f_search)

    if a_eval := node.get("eval"):
        context = _prepare_eval_context(self, env, f_model)
        try:
            return safe_eval(a_eval, context)
        except Exception as exc:
            logging.getLogger("odoo.tools.convert.init").error(
                "Could not eval(%s) for %s in %s",
                a_eval,
                node.get("name"),
                env.context,
            )
            _debug.logic(
                "convert.value.eval_failed",
                module=self.module,
                field=node.get("name"),
                error=type(exc).__name__,
            )
            raise

    if t in ("xml", "html"):
        return _eval_xml_markup(self, node, t)
    return _eval_xml_literal(self, node, env, t)


def _eval_xml_function_args(
    self: Any, node: etree._Element, env: Environment, model_str: str | None
) -> tuple[list, dict]:
    args: list = []
    kwargs: dict = {}
    if a_eval := node.get("eval"):
        context = _prepare_eval_context(self, env, model_str)
        args = list(safe_eval(a_eval, context))
    for child in node:
        if child.tag == "value" and child.get("name"):
            kwargs[child.get("name")] = _eval_xml(self, child, env)
        else:
            args.append(_eval_xml(self, child, env))
    return args, kwargs


def _eval_xml_function(self: Any, node: etree._Element, env: Environment) -> Any:
    method_name = node.get("name") or ""
    if "__" in method_name or method_name in _UNSAFE_ATTRIBUTES:
        raise NameError(f"Access to forbidden name {method_name!r}")

    from odoo.models import BaseModel

    model_str = node.get("model")
    model = env[model_str]
    args, kwargs = _eval_xml_function_args(self, node, env, model_str)

    if "context" in kwargs:
        model = model.with_context(**kwargs.pop("context"))
    method = getattr(model, method_name)
    if not getattr(method, "_api_model", False):
        record_ids, *args = args
        model = model.browse(record_ids)
        method = getattr(model, method_name)
    with _debug.perf(
        "convert.function",
        cr=env.cr,
        module=self.module,
        model=model_str,
        method=method_name,
        records=len(model),
        args=len(args),
        kwargs=sorted(kwargs),
    ):
        result = method(*args, **kwargs)
    return result.ids if isinstance(result, BaseModel) else result


def _eval_xml(self: Any, node: etree._Element, env: Environment) -> Any:
    if node.tag in ("field", "value"):
        return _eval_xml_field(self, node, env)
    if node.tag == "function":
        return _eval_xml_function(self, node, env)
    return None


def nodeattr2bool(node: etree._Element, attr: str, default: bool = False) -> bool:
    if not node.get(attr):
        return default
    val = node.get(attr).strip()
    if not val:
        return default
    return str2bool(val, default=True)


class xml_import:
    def get_env(
        self, node: etree._Element, eval_context: dict[str, Any] | None = None
    ) -> Environment:
        uid = node.get("uid")
        context = node.get("context")
        if uid or context:
            _debug.logic(
                "convert.env_switched",
                module=self.module,
                tag=node.tag,
                uid=uid,
                context=bool(context),
            )
            return self.env(
                user=uid and self.id_get(uid),
                context=context
                and {
                    **self.env.context,
                    **safe_eval(context, {"ref": self.id_get, **(eval_context or {})}),
                },
            )
        return self.env

    def normalize_xml_id(self, xml_id: str) -> str:
        if not xml_id or "." in xml_id:
            return xml_id
        return "%s.%s" % (self.module, xml_id)

    def _test_xml_id(self, xml_id: str) -> None:
        if "." in xml_id:
            module, id = xml_id.split(".", 1)
            assert "." not in id, """The ID reference "%s" must contain
maximum one dot. They are used to refer to other modules ID, in the
form: module.record_id""" % (xml_id,)
            if module != self.module:
                modcnt = self.env["ir.module.module"].search_count(
                    [("name", "=", module), ("state", "=", "installed")]
                )
                assert modcnt == 1, (
                    """The ID "%s" refers to an uninstalled module""" % (xml_id,)
                )

    def _tag_delete(self, rec: etree._Element) -> None:
        d_model = rec.get("model")
        records = self.env[d_model]

        if d_search := rec.get("search"):
            context = _prepare_eval_context(self, self.env, d_model)
            try:
                records = records.search(safe_eval(d_search, context))
            except ValueError:
                _logger.warning(
                    "Skipping deletion for failed search `%r`",
                    d_search,
                    exc_info=True,
                )
                _debug.logic(
                    "convert.delete.search_failed", module=self.module, model=d_model
                )

        if d_id := rec.get("id"):
            try:
                records += records.browse(self.id_get(d_id))
            except ValueError:
                _logger.warning(
                    "Skipping deletion for missing XML ID `%r`",
                    d_id,
                    exc_info=True,
                )
                _debug.logic(
                    "convert.delete.xml_id_missing", module=self.module, xml_id=d_id
                )

        _debug.lifecycle(
            "convert.delete",
            module=self.module,
            model=d_model,
            xml_id=d_id or None,
            searched=bool(d_search),
            records=len(records),
        )
        if records:
            records.unlink()

    def _tag_function(self, rec: etree._Element) -> None:
        if self.noupdate and self.mode != "init":
            _debug.logic(
                "convert.function.noupdate_skipped",
                module=self.module,
                model=rec.get("model"),
                method=rec.get("name"),
                mode=self.mode,
            )
            return
        env = self.get_env(rec)
        _eval_xml(self, rec, env)

    def _tag_menuitem(self, rec: etree._Element, parent: int | None = None) -> None:
        rec_id = rec.attrib["id"]
        self._test_xml_id(rec_id)

        values: dict[str, Any] = {
            "parent_id": False,
            "active": nodeattr2bool(rec, "active", default=True),
        }

        if rec.get("sequence"):
            values["sequence"] = int(rec.get("sequence"))

        if parent is not None:
            values["parent_id"] = parent
        elif rec.get("parent"):
            values["parent_id"] = self.id_get(rec.attrib["parent"])
        elif rec.get("web_icon"):
            values["web_icon"] = rec.attrib["web_icon"]

        if rec.get("name"):
            values["name"] = rec.attrib["name"]

        if rec.get("web_keywords"):
            values["web_keywords"] = rec.attrib["web_keywords"]

        if rec.get("action"):
            a_action = rec.attrib["action"]

            if "." not in a_action:
                a_action = "%s.%s" % (self.module, a_action)
            act: Any = self.env.ref(a_action).sudo()
            values["action"] = "%s,%d" % (act.type, act.id)

            if (
                not values.get("name")
                and act.type.endswith(
                    ("act_window", "wizard", "url", "client", "server")
                )
                and act.name
            ):
                values["name"] = act.name

        if not values.get("name"):
            values["name"] = rec_id or "?"

        from odoo.fields import Command

        groups: list[CommandValue] = []
        for group in split_refs(rec.get("groups", "")):
            if group.startswith("-"):
                group_id = self.id_get(group[1:])
                groups.append(Command.unlink(group_id))
            elif group:
                group_id = self.id_get(group)
                groups.append(Command.link(group_id))
        if groups:
            values["group_ids"] = groups

        data = {
            "xml_id": self.normalize_xml_id(rec_id),
            "values": values,
            "noupdate": self.noupdate,
        }
        menu = self.env["ir.ui.menu"]._load_records([data], self.mode == "update")
        menu_id = menu.id
        _debug.pipeline(
            "convert.menuitem",
            module=self.module,
            xml_id=data["xml_id"],
            menu=menu_id,
            parent=values["parent_id"],
            action=values.get("action"),
            groups=len(groups),
            children=len(rec.findall("menuitem")),
        )
        for child in rec.iterchildren("menuitem"):
            self._tag_menuitem(
                child, parent=menu_id if isinstance(menu_id, int) else None
            )

    def _noupdate_skips_record(
        self, rec: etree._Element, env: Environment, xid: str
    ) -> bool:
        if record := env["ir.model.data"]._load_xmlid(xid):
            for child in rec.xpath(".//record[@id]"):
                sub_xid = child.get("id")
                self._test_xml_id(sub_xid)
                sub_xid = self.normalize_xml_id(sub_xid)
                if sub_record := env["ir.model.data"]._load_xmlid(sub_xid):
                    self.idref[sub_xid] = sub_record.id

            self.idref[xid] = record.id
            return True
        return not nodeattr2bool(rec, "forcecreate", True)

    def _eval_field_search(
        self,
        env: Environment,
        rec_model: str,
        field: etree._Element,
        f_name: str,
        f_model: str | None,
        f_search: str,
    ) -> Any:
        from odoo.fields import Command

        f_model = _check_model_name(f_model)
        context = _prepare_eval_context(self, env, f_model)
        q = safe_eval(f_search, context)
        s = env[f_model].search(q)
        f_use = field.get("use", "") or "id"
        _fields = env[rec_model]._fields
        if (f_name in _fields) and _fields[f_name].type == "many2many":
            return [Command.set([x[f_use] for x in s])]
        return s[0][f_use] if len(s) else False

    def _eval_field_ref(
        self,
        rec: etree._Element,
        model: BaseModel,
        f_name: str,
        f_ref: str,
        xid: str,
    ) -> Any:
        if f_name in model._fields and model._fields[f_name].type == "reference":
            val = self.model_id_get(f_ref)
            return val[0] + "," + str(val[1])

        f_val = self.id_get(
            f_ref, raise_if_not_found=nodeattr2bool(rec, "forcecreate", True)
        )
        if not f_val:
            _logger.warning(
                "Skipping creation of %r because %s=%r could not be resolved",
                xid,
                f_name,
                f_ref,
            )
            _debug.logic(
                "convert.record.aborted_unresolved_ref",
                module=self.module,
                xml_id=xid,
                field=f_name,
                ref=f_ref,
            )
            return _ABORT_RECORD
        return f_val

    def _eval_field_value(
        self,
        env: Environment,
        model: BaseModel,
        field: etree._Element,
        f_name: str,
        sub_records: list[tuple[etree._Element, str]],
    ) -> Any:
        f_val = _eval_xml(self, field, env)
        if f_name not in model._fields:
            return f_val

        match model._fields[f_name].type:
            case "many2one":
                return int(f_val) if f_val else False
            case "integer":
                return int(f_val)
            case "float" | "monetary":
                return float(f_val)
            case "boolean" if isinstance(f_val, str):
                return str2bool(f_val, default=True)
            case "one2many":
                o2m_field: Any = model._fields[f_name]
                sub_records.extend(
                    (child, o2m_field.inverse_name)
                    for child in field.iterchildren("record")
                )
                _debug.logic(
                    "convert.value.one2many",
                    module=self.module,
                    model=model._name,
                    field=f_name,
                    inline_records=len(field.findall("record")),
                    skipped=isinstance(f_val, str),
                )
                return _SKIP_FIELD if isinstance(f_val, str) else f_val
            case "html" if field.get("type") == "xml":
                _logger.warning('HTML field %r is declared as `type="xml"`', f_name)
        return f_val

    def _eval_record_fields(
        self,
        rec: etree._Element,
        env: Environment,
        model: BaseModel,
        rec_model: str,
        xid: str,
        sub_records: list[tuple[etree._Element, str]],
    ) -> dict[str, Any] | None:
        res: dict[str, Any] = {}
        for field in rec.iterchildren("field"):
            f_name = field.get("name")
            if "@" in f_name:
                continue
            f_model = field.get("model")
            if not f_model and f_name in model._fields:
                f_model = model._fields[f_name].comodel_name

            if f_search := field.get("search"):
                f_val = self._eval_field_search(
                    env, rec_model, field, f_name, f_model, f_search
                )
            elif f_ref := field.get("ref"):
                f_val = self._eval_field_ref(rec, model, f_name, f_ref, xid)
            else:
                f_val = self._eval_field_value(env, model, field, f_name, sub_records)

            if f_val is _ABORT_RECORD:
                return None
            if f_val is _SKIP_FIELD:
                continue
            res[f_name] = f_val
        return res

    def _tag_record(
        self, rec: etree._Element, extra_vals: dict[str, Any] | None = None
    ) -> tuple[str, int] | None:
        rec_model = rec.get("model")
        env = self.get_env(rec)
        rec_id = rec.get("id", "")

        model = env[rec_model]

        if self.xml_filename and rec_id:
            model = model.with_context(
                install_mode=True,
                install_module=self.module,
                install_filename=self.xml_filename,
                install_xmlid=rec_id,
            )

        self._test_xml_id(rec_id)
        xid = self.normalize_xml_id(rec_id)

        if self.noupdate and self.mode != "init":
            if not rec_id:
                _debug.logic(
                    "convert.record.noupdate_anonymous_skipped",
                    module=self.module,
                    model=rec_model,
                )
                return None
            if self._noupdate_skips_record(rec, env, xid):
                _debug.logic(
                    "convert.record.noupdate_skipped",
                    module=self.module,
                    xml_id=xid,
                    model=rec_model,
                )
                return None

        foreign_record_to_create = False
        if xid and xid.partition(".")[0] != self.module:
            record = self.env["ir.model.data"]._load_xmlid(xid)
            _debug.logic(
                "convert.record.foreign",
                module=self.module,
                xml_id=xid,
                model=rec_model,
                exists=bool(record),
                forcecreate=nodeattr2bool(rec, "forcecreate"),
            )
            if not record and not (
                foreign_record_to_create := nodeattr2bool(rec, "forcecreate")
            ):
                if self.noupdate and not nodeattr2bool(rec, "forcecreate", True):
                    _debug.logic(
                        "convert.record.foreign_missing_skipped",
                        module=self.module,
                        xml_id=xid,
                    )
                    return None
                raise ValueError("Cannot update missing record %r" % xid)

        sub_records: list[tuple[etree._Element, str]] = []
        res = self._eval_record_fields(rec, env, model, rec_model, xid, sub_records)
        if res is None:
            return None

        if extra_vals:
            res.update(extra_vals)
        if "sequence" not in res and "sequence" in model._fields:
            sequence = self.next_sequence()
            if sequence:
                res["sequence"] = sequence
                _debug.logic(
                    "convert.record.auto_sequence",
                    module=self.module,
                    xml_id=xid or None,
                    sequence=sequence,
                )

        data = {"xml_id": xid, "values": res, "noupdate": self.noupdate}
        if foreign_record_to_create:
            model = model.with_context(
                foreign_record_to_create=foreign_record_to_create
            )
        record = model._load_records([data], self.mode == "update")
        if xid:
            self.idref[xid] = record.id
        _debug.pipeline(
            "convert.record",
            module=self.module,
            model=rec_model,
            xml_id=xid or None,
            record=record.id,
            fields=len(res),
            sub_records=len(sub_records),
            update=self.mode == "update",
        )
        if config.get("import_partial"):
            _debug.lifecycle(
                "convert.record.partial_commit", module=self.module, xml_id=xid or None
            )
            env.cr.commit()
        for child_rec, inverse_name in sub_records:
            self._tag_record(child_rec, extra_vals={inverse_name: record.id})
        return rec_model, record.id

    def _tag_template(self, el: etree._Element) -> tuple[str, int] | None:
        tpl_id = el.get("id", el.get("t-name"))
        full_tpl_id = tpl_id
        if "." not in full_tpl_id:
            full_tpl_id = "%s.%s" % (self.module, tpl_id)
        if not el.get("inherit_id"):
            el.set("t-name", full_tpl_id)
            el.tag = "t"
        else:
            el.tag = "data"
        el.attrib.pop("id", None)

        if self.module.startswith("theme_"):
            model = "theme.ir.ui.view"
        else:
            model = "ir.ui.view"

        record_attrs = {
            "id": tpl_id,
            "model": model,
        }
        for att in ["forcecreate", "context"]:
            if att in el.attrib:
                record_attrs[att] = el.attrib.pop(att)

        Field = builder.E.field
        name = el.get("name", tpl_id)

        record = etree.Element("record", attrib=record_attrs)
        record.append(Field(name, name="name"))
        record.append(Field(el.get("key", full_tpl_id), name="key"))
        record.append(Field("qweb", name="type"))
        if "track" in el.attrib:
            record.append(Field(el.get("track"), name="track"))
        if "priority" in el.attrib:
            record.append(Field(el.get("priority"), name="priority"))
        if "inherit_id" in el.attrib:
            record.append(Field(name="inherit_id", ref=el.get("inherit_id")))
        if "website_id" in el.attrib:
            record.append(Field(name="website_id", ref=el.get("website_id")))
        if el.get("active") in ("True", "False"):
            view_id = self.id_get(tpl_id, raise_if_not_found=False)
            if self.mode != "update" or not view_id:
                record.append(Field(name="active", eval=el.get("active")))

        if el.get("customize_show") in ("True", "False"):
            record.append(Field(name="customize_show", eval=el.get("customize_show")))
        groups = el.attrib.pop("groups", None)
        if groups:
            grp_lst = [("ref('%s')" % x) for x in split_refs(groups)]
            record.append(
                Field(
                    name="group_ids",
                    eval="[Command.set([" + ", ".join(grp_lst) + "])]",
                )
            )
        if el.get("primary") == "True":
            el.append(
                builder.E.xpath(
                    builder.E.attribute(full_tpl_id, name="t-name"),
                    expr=".",
                    position="attributes",
                )
            )
            record.append(Field("primary", name="mode"))
        record.append(Field(el, name="arch", type="xml"))

        _debug.pipeline(
            "convert.template",
            module=self.module,
            xml_id=full_tpl_id,
            model=model,
            inherit=el.get("inherit_id"),
            primary=el.get("primary") == "True",
            groups=bool(groups),
        )
        return self._tag_record(record)

    def _tag_asset(self, el: etree._Element) -> tuple[str, int] | None:
        asset_id = el.get("id")
        Field = builder.E.field

        record = etree.Element(
            "record",
            attrib={
                "id": asset_id,
                "model": (
                    "theme.ir.asset" if self.module.startswith("theme_") else "ir.asset"
                ),
            },
        )

        name = el.get("name", asset_id)
        record.append(Field(name, name="name"))

        bundle_el = el.find("bundle")
        record.append(Field(bundle_el.text, name="bundle"))
        if "directive" in bundle_el.attrib:
            record.append(Field(bundle_el.get("directive"), name="directive"))

        record.append(Field(el.find("path").text, name="path"))

        if el.get("active") in ("True", "False"):
            record_id = self.id_get(asset_id, raise_if_not_found=False)
            if self.mode != "update" or not record_id:
                record.append(Field(name="active", eval=el.get("active")))

        for child in el.iterchildren("field"):
            record.append(child)

        _debug.pipeline(
            "convert.asset",
            module=self.module,
            xml_id=asset_id,
            bundle=bundle_el.text,
            directive=bundle_el.get("directive"),
        )
        return self._tag_record(record)

    def id_get(
        self, id_str: str, raise_if_not_found: bool = True
    ) -> int | Literal[False]:
        id_str = self.normalize_xml_id(id_str)
        if id_str in self.idref:
            return self.idref[id_str]
        _debug.perf.count("convert.idref_miss", module=self.module, xml_id=id_str)
        return self.model_id_get(id_str, raise_if_not_found)[1]

    def model_id_get(
        self, id_str: str, raise_if_not_found: bool = True
    ) -> tuple[str, int | Literal[False]]:
        id_str = self.normalize_xml_id(id_str)
        return self.env["ir.model.data"]._xmlid_to_res_model_res_id(
            id_str, raise_if_not_found=raise_if_not_found
        )

    def _tag_root(self, el: etree._Element) -> None:
        env = self.get_env(el)
        noupdate = nodeattr2bool(el, "noupdate", self.noupdate)
        sequence = 0 if nodeattr2bool(el, "auto_sequence", False) else None
        self.envs.append(env)
        self._noupdate.append(noupdate)
        self._sequences.append(sequence)
        _debug.pipeline(
            "convert.data_root",
            module=self.module,
            file=self.xml_filename,
            tag=el.tag,
            noupdate=noupdate,
            auto_sequence=sequence is not None,
            depth=len(self.envs),
            children=len(el),
        )
        try:
            for rec in el:
                f = self._tags.get(rec.tag)
                if f is None:
                    if _debug.logic.enabled and isinstance(rec.tag, str):
                        _debug.logic(
                            "convert.tag_ignored", module=self.module, tag=rec.tag
                        )
                    continue
                try:
                    f(rec)
                except ParseError:
                    raise
                except ValidationError as err:
                    msg = "while parsing {file}:{viewline}\n{err}\n\nView error context:\n{context}\n".format(
                        file=rec.getroottree().docinfo.URL,
                        viewline=rec.sourceline,
                        context=pprint.pformat(
                            getattr(err, "context", None) or "-no context-"
                        ),
                        err=err.args[0],
                    )
                    _logger.debug(msg, exc_info=True)
                    _debug.logic(
                        "convert.parse_error",
                        module=self.module,
                        file=self.xml_filename,
                        tag=rec.tag,
                        line=rec.sourceline,
                        error="ValidationError",
                    )
                    raise ParseError(msg) from None
                except Exception as e:
                    _debug.logic(
                        "convert.parse_error",
                        module=self.module,
                        file=self.xml_filename,
                        tag=rec.tag,
                        line=rec.sourceline,
                        error=type(e).__name__,
                    )
                    raise ParseError(
                        "while parsing %s:%s, somewhere inside\n%s"
                        % (
                            rec.getroottree().docinfo.URL,
                            rec.sourceline,
                            etree.tostring(rec, encoding="unicode").rstrip(),
                        )
                    ) from e
        finally:
            self._noupdate.pop()
            self.envs.pop()
            self._sequences.pop()

    @property
    def env(self) -> Environment:
        return self.envs[-1]

    @property
    def noupdate(self) -> bool:
        return self._noupdate[-1]

    def next_sequence(self) -> int | None:
        value = self._sequences[-1]
        if value is not None:
            value = self._sequences[-1] = value + 10
        return value

    def __init__(
        self,
        env: Environment,
        module: str,
        idref: IdRef | None,
        mode: ConvertMode,
        noupdate: bool = False,
        xml_filename: str = "",
    ) -> None:
        self.mode = mode
        self.module = module
        self.envs = [env(context=dict(env.context, lang=None, install_module=module))]
        self.idref: IdRef = {} if idref is None else idref
        self._noupdate = [noupdate]
        self._sequences: list[int | None] = [None]
        self.xml_filename = xml_filename
        self._tags: dict[str, Callable[[etree._Element], Any]] = {
            "record": self._tag_record,
            "delete": self._tag_delete,
            "function": self._tag_function,
            "menuitem": self._tag_menuitem,
            "template": self._tag_template,
            "asset": self._tag_asset,
            **dict.fromkeys(self.DATA_ROOTS, self._tag_root),
        }

    def parse(self, de: etree._Element) -> None:
        assert de.tag in self.DATA_ROOTS, "Root xml tag must be <odoo> or <data>."
        with _debug.perf(
            "convert.xml_file",
            cr=self.env.cr,
            module=self.module,
            file=self.xml_filename,
            mode=self.mode,
            noupdate=self.noupdate,
            nodes=len(de),
        ) as span:
            self._tag_root(de)
            span.set(idrefs=len(self.idref))

    DATA_ROOTS = ["odoo", "data"]


def convert_file(
    env: Environment,
    module: str,
    filename: str,
    idref: IdRef | None,
    mode: ConvertMode = "update",
    noupdate: bool = False,
    kind: str | None = None,
    pathname: str | None = None,
) -> None:
    if kind is not None:
        warnings.warn(
            "The `kind` argument is deprecated in Odoo 19.",
            DeprecationWarning,
            stacklevel=2,
        )
    if pathname is None:
        pathname = str(Path(module, filename))
    ext = Path(filename).suffix.lower()

    _debug.pipeline(
        "convert.file",
        module=module,
        file=pathname,
        ext=ext,
        mode=mode,
        noupdate=noupdate,
        idrefs=None if idref is None else len(idref),
    )
    with file_open(pathname, "rb", env=env) as fp:
        if ext == ".csv":
            convert_csv_import(env, module, pathname, fp.read(), idref, mode, noupdate)
        elif ext == ".sql":
            convert_sql_import(env, fp)
        elif ext == ".xml":
            convert_xml_import(env, module, fp, idref, mode, noupdate)
        elif ext == ".js":
            pass
        else:
            msg = "Can't load unknown file type %s."
            raise ValueError(msg, filename)


def convert_sql_import(env: Environment, fp: IO[bytes]) -> None:
    script = fp.read()
    with _debug.perf(
        "convert.sql_file",
        cr=env.cr,
        file=getattr(fp, "name", None),
        size=len(script),
    ):
        env.cr.execute(script)


def convert_csv_import(
    env: Environment,
    module: str,
    fname: str,
    csvcontent: bytes,
    idref: IdRef | None = None,
    mode: ConvertMode = "init",
    noupdate: bool = False,
) -> None:
    env = env(context=dict(env.context, lang=None))
    filename = Path(fname).stem
    model = filename.split("-")[0]
    reader = csv.reader(
        io.StringIO(csvcontent.decode("utf-8-sig")), quotechar='"', delimiter=","
    )
    fields = next(reader)

    if not (mode == "init" or "id" in fields):
        _logger.error(
            "Import specification for %s does not contain 'id', and this is an "
            "update rather than an initial install, so existing records cannot "
            "be matched. Cannot continue.",
            fname,
        )
        _debug.logic("convert.csv.no_id_column", module=module, file=fname, mode=mode)
        return

    translate_indexes = {i for i, field in enumerate(fields) if "@" in field}

    def remove_translations(row: list[str]) -> list[str]:
        return [cell for i, cell in enumerate(row) if i not in translate_indexes]

    fields = remove_translations(fields)
    if _debug.logic.enabled and translate_indexes:
        _debug.logic(
            "convert.csv.translated_columns_dropped",
            module=module,
            file=fname,
            columns=len(translate_indexes),
        )
    if not fields:
        _debug.logic("convert.csv.no_columns", module=module, file=fname)
        return

    datas = [
        data_line for line in reader if any(data_line := remove_translations(line))
    ]

    context = {
        "mode": mode,
        "module": module,
        "install_mode": True,
        "install_module": module,
        "install_filename": fname,
        "noupdate": noupdate,
    }
    with _debug.perf(
        "convert.csv_file",
        cr=env.cr,
        module=module,
        file=fname,
        model=model,
        mode=mode,
        rows=len(datas),
        columns=len(fields),
    ) as span:
        result = env[model].with_context(**context).load(fields, datas)
        span.set(ids=len(result["ids"] or ()), messages=len(result["messages"]))
    if any(msg["type"] == "error" for msg in result["messages"]):
        warning_msg = "\n".join(msg["message"] for msg in result["messages"])
        _debug.logic(
            "convert.csv.load_failed",
            module=module,
            file=fname,
            model=model,
            errors=sum(msg["type"] == "error" for msg in result["messages"]),
        )
        raise ValueError(
            f"Module loading {module} failed: "
            f"file {fname} could not be processed:\n{warning_msg}"
        )


@functools.cache
def _get_import_relaxng() -> tuple[str, etree.RelaxNG]:
    schema = str(Path(config.root_path, "import_xml.rng"))
    return schema, etree.RelaxNG(etree.parse(schema))


def convert_xml_import(
    env: Environment,
    module: str,
    xmlfile: IO[bytes] | str,
    idref: IdRef | None = None,
    mode: ConvertMode = "init",
    noupdate: bool = False,
) -> None:
    doc = etree.parse(xmlfile)
    schema, relaxng = _get_import_relaxng()
    xml_filename = xmlfile if isinstance(xmlfile, str) else xmlfile.name
    try:
        with _debug.perf("convert.xml_schema_check", module=module, file=xml_filename):
            relaxng.assert_(doc)
    except Exception:
        _logger.exception(
            "The XML file '%s' does not fit the required schema!", xml_filename
        )
        if jingtrang:
            p = subprocess.run(
                ["pyjing", schema, xml_filename], stdout=subprocess.PIPE, check=False
            )
            _logger.warning(p.stdout.decode())
        else:
            for e in relaxng.error_log:
                _logger.warning(e)
            _logger.info(
                "Install 'jingtrang' for more precise and useful validation messages."
            )
        raise

    obj = xml_import(
        env, module, idref, mode, noupdate=noupdate, xml_filename=xml_filename
    )
    obj.parse(doc.getroot())


def reload_records(
    env: Environment, module: str, filename: str, xmlids: Iterable[str]
) -> None:
    """Re-import records a module's data file declares inside a ``noupdate`` block.

    An update leaves such records untouched once they exist, which is what keeps a
    customised record alive; a migration that changes what the module ships needs
    the opposite for the records it names. They are loaded as at installation and
    stay ``noupdate``, so the following updates skip them again.
    """
    wanted = set(xmlids)
    path = file_path(f"{module}/{filename}")
    source = etree.parse(path)
    root = etree.Element("odoo")
    data = etree.SubElement(root, "data")
    for record in source.iter("record"):
        if record.get("id") in wanted:
            data.append(record)
    if missing := wanted - {record.get("id") for record in data}:
        raise ValueError(f"{module}/{filename} declares no record {sorted(missing)}")
    content = io.BytesIO(etree.tostring(root))
    content.name = path
    convert_xml_import(env, module, content, mode="init", noupdate=True)
