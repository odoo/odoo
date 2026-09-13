import base64
import io
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import babel
from lxml import etree, html
from markupsafe import Markup, escape_silent
from PIL import Image as I

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.datetime import timezone
from odoo.tools import posix_to_ldml
from odoo.tools.json import scriptsafe as json_safe
from odoo.tools.misc import babel_locale_parse, file_open, get_lang

from odoo.addons.base.models.ir_qweb import indent_code

REMOTE_CONNECTION_TIMEOUT = 2.5
REMOTE_IMAGE_MAX_BYTES = 20 * 1024 * 1024

_logger = logging.getLogger(__name__)


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _compile_node(self, el, compile_context, level):
        snippet_key = compile_context.get("snippet-key")

        template = compile_context.ref_name
        sub_call_key = compile_context.get("snippet-sub-call-key")

        if (
            not template
            or template not in {snippet_key, sub_call_key}
            or el.getparent() is not None
        ):
            return super()._compile_node(el, compile_context, level)

        snippet_base_node = el
        if el.tag == "t":
            el_children = [
                child
                for child in list(el)
                if isinstance(child.tag, str) and child.tag != "t"
            ]
            if len(el_children) == 1:
                snippet_base_node = el_children[0]
            elif not el_children:
                el_children = [
                    child for child in list(el) if isinstance(child.tag, str)
                ]
                if len(el_children) == 1:
                    sub_call = el_children[0].get("t-call")
                    if sub_call:
                        el_children[0].set(
                            "t-options",
                            f"{{'snippet-key': '{snippet_key}', 'snippet-sub-call-key': '{sub_call}'}}",
                        )
        if "data-snippet" not in snippet_base_node.attrib:
            snippet_base_node.attrib["data-snippet"] = snippet_key.split(".", 1)[-1]
        snippet_name = compile_context.get("snippet-name")
        if snippet_name and "data-name" not in snippet_base_node.attrib:
            snippet_base_node.attrib["data-name"] = snippet_name
        return super()._compile_node(el, compile_context, level)

    def _get_preload_attribute_xmlids(self):
        return super()._get_preload_attribute_xmlids() + ["t-snippet", "t-snippet-call"]

    def _compile_directive_snippet(self, el, compile_context, indent):
        key = el.attrib.pop("t-snippet")
        el.set("t-call", key)
        snippet_lang = self.env.context.get("snippet_lang")
        if snippet_lang:
            el.set("t-lang", repr(snippet_lang))

        el.set("t-options", f"{{'snippet-key': {key!r}}}")
        view = self.env["ir.ui.view"]._get_template_view(key)
        name = el.attrib.pop("string", view.name)
        thumbnail = el.attrib.pop("t-thumbnail", "oe-thumbnail")
        image_preview = el.attrib.pop("t-image-preview", None)
        forbid_sanitize = el.attrib.pop("t-forbid-sanitize", None)
        grid_column_span = el.attrib.pop("t-grid-column-span", None)
        snippet_group = el.attrib.pop("snippet-group", None)
        group = el.attrib.pop("group", None)
        label = el.attrib.pop("label", None)
        div = Markup(
            '<div name="%s" data-oe-type="snippet" data-o-image-preview="%s" data-oe-thumbnail="%s" data-oe-snippet-id="%s" data-oe-snippet-key="%s" data-oe-keywords="%s" %s %s %s %s %s>'
        ) % (
            name,
            escape_silent(image_preview),
            thumbnail,
            view.id,
            key.split(".")[-1],
            escape_silent(el.findtext("keywords")),
            Markup('data-oe-forbid-sanitize="%s"') % forbid_sanitize
            if forbid_sanitize
            else "",
            Markup('data-o-grid-column-span="%s"') % grid_column_span
            if grid_column_span
            else "",
            Markup('data-o-snippet-group="%s"') % snippet_group
            if snippet_group
            else "",
            Markup('data-o-group="%s"') % group if group else "",
            Markup('data-o-label="%s"') % label if label else "",
        )
        self._add_text(div, compile_context)
        code = self._compile_node(el, compile_context, indent)
        self._add_text("</div>", compile_context)
        return code

    def _compile_directive_snippet_call(self, el, compile_context, indent):
        key = el.attrib.pop("t-snippet-call")
        snippet_name = el.attrib.pop("string", None)
        el.set("t-call", key)
        el.set(
            "t-options", f"{{'snippet-key': {key!r}, 'snippet-name': {snippet_name!r}}}"
        )
        return self._compile_node(el, compile_context, indent)

    def _compile_directive_install(self, el, compile_context, indent):
        key = el.attrib.pop("t-install")
        thumbnail = el.attrib.pop("t-thumbnail", "oe-thumbnail")
        image_preview = el.attrib.pop("t-image-preview", None)
        group = el.attrib.pop("group", None)
        label = el.attrib.pop("label", None)
        name = el.attrib.pop("string", None) or "Snippet"
        code = self._flush_text(compile_context, indent)
        code.append(
            indent_code(
                f"yield from self._render_install_placeholder({key!r}, {name!r}, "
                f"{thumbnail!r}, {image_preview!r}, {group!r}, {label!r})",
                indent,
            )
        )
        return code

    def _render_install_placeholder(
        self, key, name, thumbnail, image_preview, group, label
    ):
        """Emit the "install this module" placeholder, deciding at render time."""
        if not self.env.user.has_group("base.group_system"):
            return
        module = self.env["ir.module.module"].search([("name", "=", key)])
        if not module or module.state == "installed":
            return
        yield Markup(
            '<div name="%s" data-oe-type="snippet" data-module-id="%s" data-module-display-name="%s" data-o-image-preview="%s" data-oe-thumbnail="%s" %s %s><section/></div>'
        ) % (
            name,
            module.id,
            module.display_name,
            escape_silent(image_preview),
            thumbnail,
            Markup('data-o-group="%s"') % group if group else "",
            Markup('data-o-label="%s"') % label if label else "",
        )

    def _compile_directive_placeholder(self, el, compile_context, indent):
        el.set("t-att-placeholder", el.attrib.pop("t-placeholder"))
        return []

    def _get_directive_eval_order(self):
        directives = super()._get_directive_eval_order()
        index = directives.index("att") - 1
        directives.insert(index, "placeholder")
        directives.insert(index, "snippet")
        directives.insert(index, "snippet-call")
        directives.insert(index, "install")
        return directives

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ["snippet_lang"]


class IrQwebField(models.AbstractModel):
    _name = "ir.qweb.field"
    _description = "Qweb Field"
    _inherit = ["ir.qweb.field"]

    @api.model
    def attributes(self, record, field_name, options, values=None):
        attrs = super().attributes(record, field_name, options, values)
        field = record._fields.get(field_name)
        if field is None:
            return attrs

        placeholder = options.get("placeholder") or getattr(field, "placeholder", None)
        if placeholder:
            attrs["placeholder"] = placeholder

        if options["translate"] and field.type in ("char", "text"):
            lang = record.env.lang or "en_US"
            base_lang = record._get_base_lang()
            if lang == base_lang:
                attrs["data-oe-translation-state"] = "translated"
            else:
                base_value = record.with_context(lang=base_lang)[field_name]
                value = record[field_name]
                attrs["data-oe-translation-state"] = (
                    "translated" if base_value != value else "to_translate"
                )

        return attrs

    def value_from_string(self, value):
        return value

    @api.model
    def from_html(self, model, field, element):
        return self.value_from_string(element.text_content().strip()) or False


class IrQwebFieldInteger(models.AbstractModel):
    _name = "ir.qweb.field.integer"
    _description = "Qweb Field Integer"
    _inherit = ["ir.qweb.field.integer"]

    @api.model
    def from_html(self, model, field, element):
        lang = self.user_lang()
        value = element.text_content().strip()
        return int(value.replace(lang.thousands_sep or "", ""))


class IrQwebFieldFloat(models.AbstractModel):
    _name = "ir.qweb.field.float"
    _description = "Qweb Field Float"
    _inherit = ["ir.qweb.field.float"]

    @api.model
    def from_html(self, model, field, element):
        lang = self.user_lang()
        value = element.text_content().strip()
        return float(
            value.replace(lang.thousands_sep or "", "").replace(lang.decimal_point, ".")
        )


class IrQwebFieldMany2one(models.AbstractModel):
    _name = "ir.qweb.field.many2one"
    _description = "Qweb Field Many to One"
    _inherit = ["ir.qweb.field.many2one"]

    @api.model
    def attributes(self, record, field_name, options, values=None):
        field = record._fields[field_name]
        attrs = super().attributes(record, field_name, options, values)
        if options.get("inherit_branding"):
            many2one = record[field_name]
            if many2one:
                attrs["data-oe-many2one-id"] = many2one.id
                attrs["data-oe-many2one-model"] = many2one._name
            if options.get("null_text"):
                attrs["data-oe-many2one-allowreset"] = 1
                if not many2one:
                    attrs["data-oe-many2one-model"] = record._fields[
                        field_name
                    ].comodel_name
            domain = field._description_domain(self.env)
            if isinstance(domain, str):
                domain = []
            attrs["data-oe-many2one-domain"] = json_safe.dumps(domain)
        return attrs

    @api.model
    def from_html(self, model, field, element):
        Model = self.env[element.get("data-oe-model")]
        record_id = int(element.get("data-oe-id"))
        M2O = self.env[field.comodel_name]
        field_name = element.get("data-oe-field")
        many2one_id = int(element.get("data-oe-many2one-id"))

        allow_reset = element.get("data-oe-many2one-allowreset")
        if allow_reset and not many2one_id:
            Model.browse(record_id).write({field_name: False})
            return

        record = many2one_id and M2O.browse(many2one_id)
        if record and record.exists():
            Model.browse(record_id).write({field_name: many2one_id})

        return


class IrQwebFieldContact(models.AbstractModel):
    _name = "ir.qweb.field.contact"
    _description = "Qweb Field Contact"
    _inherit = ["ir.qweb.field.contact"]

    @api.model
    def attributes(self, record, field_name, options, values=None):
        attrs = super().attributes(record, field_name, options, values)
        if options.get("inherit_branding"):
            attrs["data-oe-contact-options"] = json.dumps(options)
        return attrs

    @api.model
    def get_record_to_html(self, contact_ids, options=None):
        return self.value_to_html(
            self.env["res.partner"].search([("id", "=", contact_ids[0])]),
            options=options,
        )


class IrQwebFieldDate(models.AbstractModel):
    _name = "ir.qweb.field.date"
    _description = "Qweb Field Date"
    _inherit = ["ir.qweb.field.date"]

    @api.model
    def attributes(self, record, field_name, options, values=None):
        attrs = super().attributes(record, field_name, options, values)
        if options.get("inherit_branding"):
            attrs["data-oe-original"] = record[field_name]

            if record._fields[field_name].type == "datetime":
                attrs = self.env["ir.qweb.field.datetime"].attributes(
                    record, field_name, options, values
                )
                attrs["data-oe-type"] = "datetime"
                return attrs

            lg = get_lang(self.env, self.env.user.lang)
            locale = babel_locale_parse(lg.code)
            babel_format = value_format = posix_to_ldml(lg.date_format, locale=locale)

            if record[field_name]:
                date = fields.Date.from_string(record[field_name])
                value_format = babel.dates.format_date(
                    date, format=babel_format, locale=locale
                )

            attrs["data-oe-original-with-format"] = value_format
        return attrs

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()
        if not value:
            return False

        lg = get_lang(self.env, self.env.user.lang)
        date = datetime.strptime(value, lg.date_format)
        return fields.Date.to_string(date)


class IrQwebFieldDatetime(models.AbstractModel):
    _name = "ir.qweb.field.datetime"
    _description = "Qweb Field Datetime"
    _inherit = ["ir.qweb.field.datetime"]

    @api.model
    def attributes(self, record, field_name, options, values=None):
        attrs = super().attributes(record, field_name, options, values)

        if options.get("inherit_branding"):
            value = record[field_name]

            lg = get_lang(self.env, self.env.user.lang)
            locale = babel_locale_parse(lg.code)
            babel_format = value_format = posix_to_ldml(
                f"{lg.date_format} {lg.time_format}", locale=locale
            )
            tz = record.env.context.get("tz") or self.env.user.tz

            if isinstance(value, str):
                value = fields.Datetime.from_string(value)

            if value:
                value = fields.Datetime.context_timestamp(
                    self.with_context(tz=tz), timestamp=value
                )
                value_format = babel.dates.format_datetime(
                    value, format=babel_format, locale=locale
                )
                value = fields.Datetime.to_string(value)

            attrs["data-oe-original"] = value
            attrs["data-oe-original-with-format"] = value_format
            attrs["data-oe-original-tz"] = tz
        return attrs

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()
        if not value:
            return False

        lg = get_lang(self.env, self.env.user.lang)
        try:
            datetime_format = f"{lg.date_format} {lg.time_format}"
            dt = datetime.strptime(value, datetime_format)
        except ValueError as err:
            raise ValidationError(
                _(
                    "The datetime %(value)s does not match the format %(format)s",
                    value=value,
                    format=datetime_format,
                )
            ) from err

        tz_name = (
            element.attrib.get("data-oe-original-tz")
            or self.env.context.get("tz")
            or self.env.user.tz
        )
        if tz_name:
            try:
                user_tz = timezone(tz_name)
                utc = UTC

                dt = dt.replace(tzinfo=user_tz).astimezone(utc)
            except Exception:
                _logger.warning(
                    "Failed to convert the value for a field of the model"
                    " %s back from the user's timezone (%s) to UTC",
                    model,
                    tz_name,
                    exc_info=True,
                )

        return fields.Datetime.to_string(dt)


class IrQwebFieldText(models.AbstractModel):
    _name = "ir.qweb.field.text"
    _description = "Qweb Field Text"
    _inherit = ["ir.qweb.field.text"]

    @api.model
    def from_html(self, model, field, element):
        return html_to_text(element)


class IrQwebFieldSelection(models.AbstractModel):
    _name = "ir.qweb.field.selection"
    _description = "Qweb Field Selection"
    _inherit = ["ir.qweb.field.selection"]

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()
        selection = field.get_description(self.env)["selection"]
        for k, v in selection:
            if value == v:
                return k

        raise ValueError(f"No value found for label {value} in selection {selection}")


class IrQwebFieldHtml(models.AbstractModel):
    _name = "ir.qweb.field.html"
    _description = "Qweb Field HTML"
    _inherit = ["ir.qweb.field.html"]

    @api.model
    def attributes(self, record, field_name, options, values=None):
        attrs = super().attributes(record, field_name, options, values)
        if options.get("inherit_branding"):
            field = record._fields[field_name]
            if field.sanitize:
                if field.sanitize_overridable:
                    if record.env.user.has_group("base.group_sanitize_override"):
                        return attrs
                    else:
                        try:
                            field.convert_to_column_insert(record[field_name], record)
                        except UserError:
                            attrs["data-oe-sanitize-prevent-edition"] = 1
                            return attrs
                attrs["data-oe-sanitize"] = (
                    "no_block"
                    if field.sanitize_attributes
                    else 1
                    if field.sanitize_form
                    else "allow_form"
                )

        return attrs

    @api.model
    def from_html(self, model, field, element):
        content = []
        if element.text:
            content.append(element.text)
        content.extend(
            html.tostring(child, encoding="unicode")
            for child in element.iterchildren(tag=etree.Element)
        )
        return "\n".join(content)


class IrQwebFieldImage(models.AbstractModel):
    _name = "ir.qweb.field.image"
    _description = "Qweb Field Image"
    _inherit = ["ir.qweb.field.image"]

    local_url_re = re.compile(r"^/(?P<module>[^/]+)/static/(?P<rest>.+)$")
    redirect_url_re = re.compile(r"\/web\/image\/\d+-redirect\/")

    @api.model
    def from_html(self, model, field, element):
        if element.find("img") is None:
            return False
        url = element.find("img").get("src")

        url_object = urlsplit(url)
        if url_object.path.startswith("/web/image"):
            fragments = url_object.path.split("/")
            query = {k: v[0] for k, v in parse_qs(url_object.query).items()}
            url_id = fragments[3].split("-")[0]
            if url_id.isdigit():
                model = "ir.attachment"
                oid = url_id
                field = "datas"
            else:
                model = query.get("model", fragments[3])
                oid = query.get("id", fragments[4])
                field = query.get("field", fragments[5])
            item = self.env[model].browse(int(oid))
            if self.redirect_url_re.match(url_object.path):
                return self.load_remote_url(item.url)
            return item[field]

        if self.local_url_re.match(url_object.path):
            return self.load_local_url(url)

        return self.load_remote_url(url)

    def load_local_url(self, url):
        match = self.local_url_re.match(urlsplit(url).path)
        rest = match.group("rest")

        path = str(Path(match.group("module")) / "static" / rest)

        try:
            with file_open(path, "rb") as f:
                image = I.open(f)
                image.load()
                f.seek(0)
                return base64.b64encode(f.read())
        except Exception:
            _logger.exception("Failed to load local image %r", url)
            return None

    def load_remote_url(self, url):
        if url.startswith("data:"):
            _logger.debug("Cannot load binary data url %r", url)
            return None
        try:
            req = self.env["ir.egress"].request(
                "GET",
                url,
                purpose="remote_image",
                timeout=REMOTE_CONNECTION_TIMEOUT,
                max_bytes=REMOTE_IMAGE_MAX_BYTES,
            )
            image = I.open(io.BytesIO(req.content))
            image.load()
        except Exception:
            _logger.warning("Failed to load remote image %r", url, exc_info=True)
            return None

        out = io.BytesIO()
        image.save(out, image.format)
        return base64.b64encode(out.getvalue())


class IrQwebFieldMonetary(models.AbstractModel):
    _inherit = "ir.qweb.field.monetary"

    @api.model
    def from_html(self, model, field, element):
        lang = self.user_lang()

        value = element.find("span").text_content().strip()

        return float(
            value.replace(lang.thousands_sep or "", "").replace(lang.decimal_point, ".")
        )


class IrQwebFieldDuration(models.AbstractModel):
    _name = "ir.qweb.field.duration"
    _description = "Qweb Field Duration"
    _inherit = ["ir.qweb.field.duration"]

    @api.model
    def attributes(self, record, field_name, options, values=None):
        attrs = super().attributes(record, field_name, options, values)
        if options.get("inherit_branding"):
            attrs["data-oe-original"] = record[field_name]
        return attrs

    @api.model
    def from_html(self, model, field, element):
        value = element.text_content().strip()

        return float(value)


class IrQwebFieldRelative(models.AbstractModel):
    _name = "ir.qweb.field.relative"
    _description = "Qweb Field Relative"
    _inherit = ["ir.qweb.field.relative"]


class IrQwebFieldQweb(models.AbstractModel):
    _name = "ir.qweb.field.qweb"
    _description = "Qweb Field qweb"
    _inherit = ["ir.qweb.field.qweb"]


def html_to_text(element):
    output = []
    _wrap(element, output)

    return re.sub(
        r"[ \t\r\f]*\n[ \t\r\f]*", "\n", "".join(_realize_padding(output)).strip()
    )


_PADDED_BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6"}
_MISC_BLOCK = {
    "address",
    "article",
    "aside",
    "audio",
    "blockquote",
    "canvas",
    "dd",
    "dl",
    "div",
    "figcaption",
    "figure",
    "footer",
    "form",
    "header",
    "hgroup",
    "hr",
    "ol",
    "output",
    "pre",
    "section",
    "tfoot",
    "ul",
    "video",
}


def _collapse_whitespace(text):
    return re.sub(r"\s+", " ", text)


def _realize_padding(it):
    padding = 0
    for item in it:
        if isinstance(item, int):
            padding = max(padding, item)
            continue

        if padding:
            yield "\n" * padding
            padding = 0

        yield item


def _wrap(element, output, wrapper=""):
    output.append(wrapper)
    if element.text:
        output.append(_collapse_whitespace(element.text))
    for child in element:
        _element_to_text(child, output)
    output.append(wrapper)


def _element_to_text(e, output):
    if e.tag == "br":
        output.append("\n")
    elif e.tag in _PADDED_BLOCK:
        _wrap(e, output, 2)
    elif e.tag in _MISC_BLOCK:
        _wrap(e, output, 1)
    else:
        _wrap(e, output)

    if e.tail:
        output.append(_collapse_whitespace(e.tail))
