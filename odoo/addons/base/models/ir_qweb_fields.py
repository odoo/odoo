import base64
import logging
import math
from datetime import date, datetime, time
from io import BytesIO
from typing import Any

import babel.dates
from lxml import etree, html
from markupsafe import Markup, escape
from PIL import Image

from odoo import api, fields, models, tools
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import guess_mimetype
from odoo.libs.numbers import float_utils
from odoo.libs.text import nl2br
from odoo.tools import (
    NEGATIVE_SIGN_JOINER,
    format_amount_parts,
    format_date,
    format_duration,
    posix_to_ldml,
)
from odoo.tools.mail import safe_attrs
from odoo.tools.misc import babel_locale_parse, get_lang
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

TIMEDELTA_UNITS = (
    ("year", 3600 * 24 * 365),
    ("month", 3600 * 24 * 30),
    ("week", 3600 * 24 * 7),
    ("day", 3600 * 24),
    ("hour", 3600),
    ("minute", 60),
    ("second", 1),
)

TIMEDELTA_SECONDS_BY_UNIT = dict(TIMEDELTA_UNITS)

CONTACT_DEFAULT_FIELDS = ("name", "address", "phone", "email")

BARCODE_RENDER_OPTIONS = frozenset(
    ("width", "height", "humanreadable", "quiet", "mask")
)


class IrQwebField(models.AbstractModel):
    _name = "ir.qweb.field"
    _description = "Qweb Field"

    @api.model
    def attributes(
        self,
        record: models.BaseModel,
        field_name: str,
        options: dict[str, Any],
        values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = {}
        if not options.get("inherit_branding") and not options.get("translate"):
            return data

        field = record._fields[field_name]
        _debug.logic(
            "attributes_branded",
            model=record._name,
            field=field_name,
            readonly=bool(field.readonly),
            translate=bool(options.get("translate")),
        )
        data["data-oe-model"] = record._name
        data["data-oe-id"] = record.id
        data["data-oe-field"] = field.name
        data["data-oe-type"] = options.get("type")
        data["data-oe-expression"] = options.get("expression")
        if field.readonly:
            data["data-oe-readonly"] = 1
        return data

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str | Markup:
        if value is None or value is False:
            return ""

        if isinstance(value, bytes):
            _debug.logic("bytes_value_decoded", bytes=len(value))
            value = value.decode(errors="replace")
        return escape(value)

    @api.model
    def _get_record_context_keys(self) -> list[str]:
        return self.env["ir.qweb"]._get_template_cache_keys() + ["tz", "bin_size"]

    @api.model
    def _record_options(
        self, record: models.BaseModel, field_name: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        return options

    @api.model
    def record_to_html(
        self, record: models.BaseModel, field_name: str, options: dict[str, Any]
    ) -> str | Markup | bool:
        if not record:
            _debug.logic("record_to_html_skipped", reason="empty_record")
            return False
        options = self._record_options(record, field_name, options)
        env_context = self.env.context
        record_context = record.env.context
        context_delta = {
            key: env_context[key]
            for key in self._get_record_context_keys()
            if key in env_context and record_context.get(key) != env_context[key]
        }
        if context_delta:
            _debug.logic(
                "record_context_realigned",
                model=record._name,
                field=field_name,
                keys=sorted(context_delta),
            )
            record = record.with_context(**context_delta)
        value = record[field_name]
        _debug.pipeline(
            "record_to_html",
            model=record._name,
            field=field_name,
            converter=self._name,
            empty=value is False or value is None,
        )
        return (
            False
            if value is False or value is None
            else self.value_to_html(value, options=options)
        )

    @api.model
    def user_lang(self) -> models.BaseModel:
        return self.env["res.lang"].browse(get_lang(self.env).id)

    @api.model
    def _format_number(
        self,
        number_format: str,
        value: Any,
        grouping: bool = True,
        lang: models.BaseModel | None = None,
    ) -> str:
        return (
            (lang or self.user_lang())
            .format(number_format, value, grouping=grouping)
            .replace("-", NEGATIVE_SIGN_JOINER)
        )


class IrQwebFieldInteger(models.AbstractModel):
    _name = "ir.qweb.field.integer"
    _description = "Qweb Field Integer"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        if options.get("format_decimalized_number"):
            return tools.misc.format_decimalized_number(
                value, options.get("precision_digits", 1)
            )
        return self._format_number("%d", value)


class IrQwebFieldFloat(models.AbstractModel):
    _name = "ir.qweb.field.float"
    _description = "Qweb Field Float"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        if not math.isfinite(value):
            _debug.logic("float_rejected", reason="not_finite")
            msg = f"The value passed to the float field is not finite: {value!r}"
            raise ValueError(msg)
        min_precision = options.get("min_precision")
        if "decimal_precision" in options:
            precision = self.env["decimal.precision"].get_precision(
                options["decimal_precision"]
            )
        elif options.get("precision") is None:
            int_digits = int(math.log10(abs(value))) + 1 if value != 0 else 1
            max_dec_digits = max(15 - int_digits, 0)
            precision = min(6, max_dec_digits)
            min_precision = min_precision or 1
        else:
            precision = options["precision"]

        fmt = f"%.{precision}f"
        _debug.logic(
            "float_precision",
            source="decimal_precision"
            if "decimal_precision" in options
            else "derived"
            if options.get("precision") is None
            else "option",
            precision=precision,
            min_precision=min_precision,
        )
        if min_precision and min_precision < precision:
            _int_part, dec_part = float_utils.float_split_str(value, precision)
            digits_count = len(dec_part.rstrip("0"))
            if digits_count < min_precision:
                fmt = f"%.{min_precision}f"
            elif digits_count < precision:
                fmt = f"%.{digits_count}f"

        value = float_utils.float_round(value, precision_digits=precision)
        return self._format_number(fmt, value)

    @api.model
    def _record_options(
        self, record: models.BaseModel, field_name: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        field = record._fields[field_name]
        defaults = {}
        if "precision" not in options and "decimal_precision" not in options:
            digits = field.get_digits(record.env)
            if digits:
                defaults["precision"] = digits[1]
        get_min_display_digits = getattr(field, "get_min_display_digits", None)
        if "min_precision" not in options and get_min_display_digits is not None:
            defaults["min_precision"] = get_min_display_digits(record.env)
        if _debug.logic.enabled and defaults:
            _debug.logic(
                "float_options_defaulted", field=field_name, keys=sorted(defaults)
            )
        return dict(options, **defaults) if defaults else options


class IrQwebFieldDate(models.AbstractModel):
    _name = "ir.qweb.field.date"
    _description = "Qweb Field Date"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        return format_date(self.env, value, date_format=options.get("format"))


class IrQwebFieldDatetime(models.AbstractModel):
    _name = "ir.qweb.field.datetime"
    _description = "Qweb Field Datetime"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        if not value:
            return ""

        lang = self.user_lang()
        locale = babel_locale_parse(lang.code)
        dateless = isinstance(value, date) and not isinstance(value, datetime)
        if isinstance(value, str):
            value = fields.Datetime.from_string(value)
        elif dateless:
            value = datetime.combine(value, time.min)

        tz_source = self
        if options.get("tz_name"):
            tz_source = self.with_context(tz=options["tz_name"])
            tzinfo = babel.dates.get_timezone(options["tz_name"])
        else:
            tzinfo = None

        if dateless:
            tzinfo = None
        else:
            value = fields.Datetime.context_timestamp(tz_source, value)

        if "format" in options:
            pattern = options["format"]
        else:
            if options.get("time_only"):
                strftime_pattern = lang.time_format
            elif options.get("date_only"):
                strftime_pattern = lang.date_format
            else:
                strftime_pattern = f"{lang.date_format} {lang.time_format}"

            pattern = posix_to_ldml(strftime_pattern, locale=locale)

        if options.get("hide_seconds"):
            pattern = pattern.replace(":ss", "").replace(":s", "")

        _debug.logic(
            "datetime_formatted",
            lang=lang.code,
            dateless=dateless,
            tz=options.get("tz_name"),
            explicit_format="format" in options,
            mode="time"
            if options.get("time_only")
            else "date"
            if options.get("date_only")
            else "datetime",
        )
        if options.get("time_only"):
            return babel.dates.format_time(
                value, format=pattern, tzinfo=tzinfo, locale=locale
            )
        elif options.get("date_only"):
            return babel.dates.format_date(value, format=pattern, locale=locale)
        else:
            return babel.dates.format_datetime(
                value, format=pattern, tzinfo=tzinfo, locale=locale
            )


class IrQwebFieldText(models.AbstractModel):
    _name = "ir.qweb.field.text"
    _description = "Qweb Field Text"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str | Markup:
        return nl2br(value) if value else ""


class IrQwebFieldSelection(models.AbstractModel):
    _name = "ir.qweb.field.selection"
    _description = "Qweb Field Selection"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str | Markup:
        if value is None or value is False:
            return ""
        selection = options.get("selection")
        if selection is None:
            _debug.logic("selection_rejected", reason="no_selection_option")
            msg = (
                "Missing 'selection' option for selection field rendering; "
                "t-out with widget='selection' must supply the label map that "
                "t-field reads off the field."
            )
            raise ValueError(msg)
        return escape(selection.get(value, value) or "")

    @api.model
    def _record_options(
        self, record: models.BaseModel, field_name: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        if "selection" in options:
            return options
        field = record._fields[field_name]
        selection = dict(field._description_selection(self.env))
        _debug.perf.count(
            "selection_labels_loaded", field=field_name, labels=len(selection)
        )
        return dict(options, selection=selection)


class IrQwebFieldMany2one(models.AbstractModel):
    _name = "ir.qweb.field.many2one"
    _description = "Qweb Field Many to One"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str | Markup | bool:
        if not value:
            return False
        value = value._filtered_display_name_access().sudo().display_name
        if not value:
            _debug.logic("many2one_hidden", reason="no_display_name_access")
            return False
        return nl2br(value)


class IrQwebFieldMany2many(models.AbstractModel):
    _name = "ir.qweb.field.many2many"
    _description = "Qweb field many2many"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str | Markup | bool:
        if not value:
            return False
        visible = value._filtered_display_name_access().sudo()
        _debug.perf.count(
            "many2many_rendered",
            model=value._name,
            records=len(value),
            visible=len(visible),
        )
        text = ", ".join(visible.mapped("display_name"))
        if not text:
            return False
        return nl2br(text)


class IrQwebFieldOne2many(models.AbstractModel):
    _name = "ir.qweb.field.one2many"
    _description = "Qweb field one2many"
    _inherit = ["ir.qweb.field.many2many"]


class IrQwebFieldHtml(models.AbstractModel):
    _name = "ir.qweb.field.html"
    _description = "Qweb Field HTML"
    _inherit = ["ir.qweb.field"]

    @api.model
    def _post_process_html_body(
        self, body: etree._Element, options: dict[str, Any]
    ) -> etree._Element:
        return body

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> Markup:
        if not value:
            return Markup("")
        qweb = self.env["ir.qweb"]
        body = etree.fromstring(
            f"<body>{value}</body>", etree.HTMLParser(encoding="utf-8")
        )[0]
        att_names = qweb._get_post_processing_att_names()
        rewritten = 0  # debuglog
        for element in body.iter():
            attrib = element.attrib
            if not attrib:
                continue
            if att_names is not None and att_names.isdisjoint(attrib):
                continue
            processed = qweb._post_processing_att(element.tag, dict(attrib))
            if len(processed) != len(attrib) or any(
                attrib.get(name) != value for name, value in processed.items()
            ):
                attrib.clear()
                attrib.update(processed)
                rewritten += 1  # debuglog
        _debug.perf.count("html_post_processed", chars=len(value), rewritten=rewritten)
        body = self._post_process_html_body(body, options)
        serialized = etree.tostring(body, encoding="unicode", method="html")
        return Markup(serialized.removeprefix("<body>").removesuffix("</body>"))


class IrQwebFieldImage(models.AbstractModel):
    _name = "ir.qweb.field.image"
    _description = "Qweb Field Image"
    _inherit = ["ir.qweb.field"]

    @api.model
    def _get_src_data_b64(self, value: Any, options: dict[str, Any]) -> str:
        if isinstance(value, (bytes, bytearray, memoryview)):
            source = bytes(value)
        elif isinstance(value, str):
            source = value
        else:
            _debug.logic("image_rejected", reason="bad_type", type=type(value).__name__)
            msg = "Invalid image content"
            raise ValueError(msg)

        try:
            img_b64 = base64.b64decode(source)
            value_b64 = source if isinstance(source, str) else source.decode("ascii")
        except ValueError:
            _debug.logic("image_rejected", reason="not_base64")
            msg = "Invalid image content"
            raise ValueError(msg) from None

        mimetype = guess_mimetype(img_b64, "") if img_b64 else None
        _debug.logic("image_sniffed", mimetype=mimetype, bytes=len(img_b64))
        if mimetype == "image/webp":
            return self.env["ir.qweb"]._get_converted_image_data_uri(value)
        elif mimetype != "image/svg+xml":
            sniffed = mimetype
            try:
                image = Image.open(BytesIO(img_b64))
                image.verify()
                mimetype = (
                    Image.MIME.get(image.format)
                    or sniffed
                    or (f"image/{image.format.lower()}" if image.format else None)
                )
                if not mimetype:
                    _debug.logic("image_rejected", reason="no_mimetype")
                    msg = "Invalid image content"
                    raise ValueError(msg)
            except OSError as exc:
                _debug.logic("image_rejected", reason="not_an_image", sniffed=sniffed)
                msg = "Non-image binary fields can not be converted to HTML"
                raise ValueError(msg) from exc
            except SyntaxError as exc:
                _debug.logic("image_rejected", reason="pil_syntax", sniffed=sniffed)
                msg = "Invalid image content"
                raise ValueError(msg) from exc

        return f"data:{mimetype};base64,{value_b64}"

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> Markup:
        return Markup('<img src="%s">') % self._get_src_data_b64(value, options)


class IrQwebFieldImageUrl(models.AbstractModel):
    _name = "ir.qweb.field.image_url"
    _description = "Qweb Field Image"
    _inherit = ["ir.qweb.field.image"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> Markup:
        return Markup('<img src="%s">') % value


class IrQwebFieldMonetary(models.AbstractModel):
    _name = "ir.qweb.field.monetary"
    _description = "Qweb Field Monetary"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> Markup:
        display_currency = options.get("display_currency")
        if not display_currency:
            _debug.logic("monetary_rejected", reason="no_display_currency")
            msg = "Missing display_currency option for monetary field rendering."
            raise ValueError(msg)

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _debug.logic(
                "monetary_rejected", reason="not_a_number", type=type(value).__name__
            )
            msg = f"The value passed to the monetary field is not a number: {value!r}"
            raise TypeError(msg)

        if options.get("from_currency"):
            conversion_date = options.get("date") or fields.Date.today()
            company_id = options.get("company_id")
            if company_id:
                company = self.env["res.company"].browse(company_id)
            else:
                company = self.env.company
            value = options["from_currency"]._convert(
                value, display_currency, company, conversion_date
            )
            _debug.logic(
                "monetary_converted",
                from_currency=options["from_currency"].id,
                to_currency=display_currency.id,
                company=company.id,
            )

        lang = self.user_lang()
        pre, formatted_amount, post = format_amount_parts(
            self.env,
            value,
            display_currency,
            lang_code=lang.code,
            decimal_places=options.get("decimal_places"),
        )

        _debug.logic(
            "monetary_formatted",
            currency=display_currency.id,
            lang=lang.code,
            decimal_places=options.get("decimal_places"),
            label_price=bool(options.get("label_price")),
        )
        if options.get("label_price") and lang.decimal_point in formatted_amount:
            sep = lang.decimal_point
            integer_part, decimal_part = formatted_amount.split(sep)
            integer_part += sep
            return Markup(
                '{pre}<span class="oe_currency_value">{0}</span><span class="oe_currency_value" style="font-size:0.5em">{1}</span>{post}'
            ).format(integer_part, decimal_part, pre=pre, post=post)

        return Markup('{pre}<span class="oe_currency_value">{0}</span>{post}').format(
            formatted_amount, pre=pre, post=post
        )

    @api.model
    def _get_currency_field_names(
        self, record: models.BaseModel, field_name: str
    ) -> list[str]:
        field = record._fields[field_name]
        declared = (
            field.get_currency_field(record) if field.type == "monetary" else None
        )
        candidates = [
            name
            for name, candidate in record._fields.items()
            if candidate.type == "many2one" and candidate.comodel_name == "res.currency"
        ]
        ranked = sorted(
            candidates,
            key=lambda name: (name not in ("currency_id", "company_currency_id"), name),
        )
        if declared:
            ranked = [declared, *(name for name in ranked if name != declared)]
        _debug.logic(
            "currency_fields_ranked",
            model=getattr(record, "_name", None),
            field=field_name,
            declared=declared,
            candidates=len(candidates),
        )
        return ranked

    @api.model
    def _record_options(
        self, record: models.BaseModel, field_name: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        options = dict(options)
        if not options.get("display_currency"):
            for name in self._get_currency_field_names(record, field_name):
                currency = record[name]
                if currency:
                    _debug.logic(
                        "display_currency_resolved", field=field_name, via=name
                    )
                    options["display_currency"] = currency
                    break
        options.setdefault("date", record.env.context.get("date"))
        options.setdefault("company_id", record.env.context.get("company_id"))
        return options


class IrQwebFieldFloatTime(models.AbstractModel):
    _name = "ir.qweb.field.float_time"
    _description = "Qweb Field Float Time"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        return format_duration(value)


class IrQwebFieldTime(models.AbstractModel):
    _name = "ir.qweb.field.time"
    _description = "QWeb Field Time"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        if value < 0:
            msg = f"The value passed to the time field should be positive: {value!r}"
            raise ValueError(msg)
        if value >= 24:
            msg = f"The hour must be between 0 and 23, got {value!r}"
            raise ValueError(msg)
        minutes_total = min(round(value * 60), 24 * 60 - 1)
        hours, minutes = divmod(minutes_total, 60)
        t = time(hour=hours, minute=minutes)

        locale = babel_locale_parse(self.user_lang().code)
        pattern = options.get("format", "short")

        return babel.dates.format_time(t, format=pattern, tzinfo=None, locale=locale)


class IrQwebFieldDuration(models.AbstractModel):
    _name = "ir.qweb.field.duration"
    _description = "Qweb Field Duration"
    _inherit = ["ir.qweb.field"]

    @api.model
    def _format_timedelta(
        self,
        seconds: float,
        add_direction: bool,
        fmt: str,
        locale: Any,
    ) -> str:
        kwargs = {"add_direction": add_direction, "format": fmt, "threshold": 1}
        try:
            return babel.dates.format_timedelta(seconds, locale=locale, **kwargs)
        except KeyError:
            _debug.logic("timedelta_format_fallback", fmt=fmt, to="long")
            kwargs["format"] = "long"
            try:
                return babel.dates.format_timedelta(seconds, locale=locale, **kwargs)
            except KeyError:
                _debug.logic("timedelta_format_fallback", fmt="long", to="en_US")
                return babel.dates.format_timedelta(
                    seconds, locale=babel_locale_parse("en_US"), **kwargs
                )

    @api.model
    def _get_timedelta_unit_seconds(self, option: str, name: str) -> int:
        try:
            return TIMEDELTA_SECONDS_BY_UNIT[name]
        except KeyError:
            _debug.logic(
                "duration_rejected", reason="unknown_unit", option=option, unit=name
            )
            known = ", ".join(TIMEDELTA_SECONDS_BY_UNIT)
            msg = (
                f"Unknown {option!r} unit {name!r} for the duration widget; "
                f"expected one of: {known}"
            )
            raise ValueError(msg) from None

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        locale = babel_locale_parse(self.user_lang().code)
        factor = self._get_timedelta_unit_seconds("unit", options.get("unit", "second"))
        round_to = self._get_timedelta_unit_seconds(
            "round", options.get("round", "second")
        )

        if options.get("digital") and round_to > 3600:
            round_to = 3600

        seconds = round((value * factor) / round_to) * round_to
        sign = "-" if seconds < 0 else ""
        remainder = abs(seconds)
        _debug.logic(
            "duration_formatted",
            factor=factor,
            round_to=round_to,
            digital=bool(options.get("digital")),
            add_direction=bool(options.get("add_direction")),
            seconds=seconds,
        )

        if options.get("digital"):
            sections = []
            for _unit, secs_per_unit in TIMEDELTA_UNITS:
                if secs_per_unit > 3600:
                    continue
                count, remainder = divmod(remainder, secs_per_unit)
                if not count and (secs_per_unit > factor or secs_per_unit < round_to):
                    continue
                sections.append("%02d" % count)
            return sign + ":".join(sections)

        fmt = options.get("format", "long")

        if options.get("add_direction"):
            return (
                ""
                if not seconds
                else self._format_timedelta(seconds, True, fmt, locale)
            )

        sections = []
        for _unit, secs_per_unit in TIMEDELTA_UNITS:
            count, remainder = divmod(remainder, secs_per_unit)
            if not count:
                continue
            section = self._format_timedelta(count * secs_per_unit, False, fmt, locale)
            if section:
                sections.append(section)

        if not sections:
            return ""
        return sign + " ".join(sections)


class IrQwebFieldRelative(models.AbstractModel):
    _name = "ir.qweb.field.relative"
    _description = "Qweb Field Relative"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str:
        locale = babel_locale_parse(self.user_lang().code)

        if isinstance(value, str):
            value = fields.Datetime.from_string(value)
        elif isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, time.min)

        reference = fields.Datetime.from_string(
            options.get("now") or fields.Datetime.now()
        )
        _debug.logic("relative_formatted", explicit_now="now" in options)

        return babel.dates.format_timedelta(
            value - reference, add_direction=True, locale=locale
        )

    @api.model
    def _record_options(
        self, record: models.BaseModel, field_name: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        if "now" in options:
            return options
        field = record._fields[field_name]
        now = field.now() if field.type == "datetime" else fields.Datetime.now()
        return dict(options, now=now)


class IrQwebFieldBarcode(models.AbstractModel):
    _name = "ir.qweb.field.barcode"
    _description = "Qweb Field Barcode"
    _inherit = ["ir.qweb.field"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str | Markup:
        if not value:
            return ""
        value = value if isinstance(value, str) else str(value)
        if not value.isascii():
            _debug.logic("barcode_skipped", reason="non_ascii", chars=len(value))
            return nl2br(value)
        barcode_symbology = options.get("symbology", "Code128")
        with _debug.perf("barcode", symbology=barcode_symbology, chars=len(value)):
            barcode = self.env["ir.actions.report"].prepare_barcode(
                barcode_symbology,
                value,
                **{k: v for k, v in options.items() if k in BARCODE_RENDER_OPTIONS},
            )

        img_element = html.Element("img")
        for k, v in options.items():
            attribute = k.removeprefix("img_")
            if k.startswith("img_") and attribute in safe_attrs:
                img_element.set(attribute, v if isinstance(v, str) else str(v))
        if not img_element.get("alt"):
            img_element.set("alt", _("Barcode %s", value))
        img_element.set(
            "src", f"data:image/png;base64,{base64.b64encode(barcode).decode()}"
        )
        return Markup(html.tostring(img_element, encoding="unicode"))


class IrQwebFieldContact(models.AbstractModel):
    _name = "ir.qweb.field.contact"
    _description = "Qweb Field Contact"
    _inherit = ["ir.qweb.field.many2one"]

    @api.model
    def value_to_html(self, value: Any, options: dict[str, Any]) -> str | Markup:
        template_options = options.get("template_options") or {}
        if not value:
            _debug.logic("contact_empty", null_text=bool(options.get("null_text")))
            if options.get("null_text"):
                return self.env["ir.qweb"]._render(
                    "base.no_contact",
                    {"options": options},
                    minimal_qcontext=True,
                    **template_options,
                )
            return ""

        field_names = options.get("fields") or CONTACT_DEFAULT_FIELDS
        if options.get("separator"):
            separator = escape(options["separator"])
        elif options.get("no_tag_br"):
            separator = escape(", ")
        else:
            separator = Markup("<br/>")

        value = value.sudo().with_context(show_address=True)
        # a record delegating to a partner (a user) renders that partner's
        # numbers; only res.partner carries them
        contact = value
        if value._name != "res.partner":
            for parent_model, parent_field in value._inherits.items():
                if parent_model == "res.partner":
                    _debug.logic(
                        "contact_delegated", model=value._name, via=parent_field
                    )
                    contact = value[parent_field]
                    break
        phone = (
            contact._phone_get_number().number
            if "phone" in field_names and contact._name == "res.partner"
            else ""
        )
        display_name = value.display_name or ""
        name_line, *address_lines = display_name.split("\n")
        if any(elem.strip() for elem in address_lines):
            address = separator.join(address_lines).strip()
        else:
            address = ""
        _debug.logic(
            "contact_rendered",
            partner=value.id,
            fields=list(field_names),
            address_lines=len(address_lines),
            separator="text"
            if options.get("separator") or options.get("no_tag_br")
            else "br",
        )
        values = {
            "name": name_line,
            "address": address,
            "phone": phone,
            "city": value.city,
            "country_id": value.country_id.display_name,
            "website": value.website,
            "email": value.email,
            "vat": value.vat,
            "vat_label": value.country_id.vat_label or _("VAT"),
            "fields": field_names,
            "object": value,
            "options": options,
        }
        return self.env["ir.qweb"]._render(
            "base.contact", values, minimal_qcontext=True, **template_options
        )


class IrQwebFieldQweb(models.AbstractModel):
    _name = "ir.qweb.field.qweb"
    _description = "Qweb Field qweb"
    _inherit = ["ir.qweb.field.many2one"]

    @api.model
    def record_to_html(
        self, record: models.BaseModel, field_name: str, options: dict[str, Any]
    ) -> str | Markup:
        view = record[field_name]
        if not view:
            _debug.logic("qweb_field_empty", field=field_name, model=record._name)
            return ""

        if view._name != "ir.ui.view":
            _logger.warning(
                "%s.%s must be a 'ir.ui.view', got %r.",
                record,
                field_name,
                view._name,
            )
            _debug.logic("qweb_field_not_a_view", field=field_name, model=view._name)
            return ""

        return self.env["ir.qweb"]._render(view.id, options.get("values", {}))
