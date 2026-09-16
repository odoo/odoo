import locale
import logging
import threading
from typing import Any, Literal, Self

from odoo import _, _lt, api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.locale import format_number
from odoo.tools import OrderedSet, reset_cached_properties
from odoo.tools.misc import ReadonlyDict

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_LOCALE_LOCK = threading.Lock()


class LangData(ReadonlyDict):
    __slots__ = ()

    def __bool__(self) -> bool:
        return bool(self.id)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError from None


class LangDataDict(ReadonlyDict):
    __slots__ = ()

    def __getitem__(self, key: Any) -> LangData:
        try:
            return self._data__[key]
        except KeyError:
            some_lang = next(iter(self.values()), None)
            if some_lang is None:
                msg = "LangData is empty: at least one active language must exist"
                raise RuntimeError(msg) from None
            return LangData(dict.fromkeys(some_lang, False))


class ResLang(models.Model):
    _name = "res.lang"
    _description = "Languages"
    _order = "active desc,name"
    _allow_sudo_commands = False

    _disallowed_datetime_patterns = list(tools.misc.DATETIME_FORMATS_MAP)
    _disallowed_datetime_patterns.remove("%y")

    def _selection_date_formats(self) -> list[tuple[str, str]]:
        current_year = fields.Date.today().year
        return [
            ("%d/%m/%Y", f"31/01/{current_year}"),
            ("%m/%d/%Y", f"01/31/{current_year}"),
            ("%Y/%m/%d", f"{current_year}/01/31"),
            ("%d-%m-%Y", f"31-01-{current_year}"),
            ("%m-%d-%Y", f"01-31-{current_year}"),
            ("%Y-%m-%d", f"{current_year}-01-31"),
            ("%d.%m.%Y", f"31.01.{current_year}"),
            ("%m.%d.%Y", f"01.31.{current_year}"),
            ("%Y.%m.%d", f"{current_year}.01.31"),
        ]

    name = fields.Char(required=True)
    code = fields.Char(
        string="Locale Code",
        required=True,
        help="This field is used to set/get locales for user",
    )
    iso_code = fields.Char(
        string="ISO code",
        help="This ISO code is the name of po files to use for translations",
    )
    url_code = fields.Char(
        string="URL Code",
        required=True,
        help="The Lang Code displayed in the URL",
    )
    active = fields.Boolean()
    direction = fields.Selection(
        selection=[("ltr", "Left-to-Right"), ("rtl", "Right-to-Left")],
        default="ltr",
        required=True,
    )
    date_format = fields.Selection(
        selection=_selection_date_formats,
        default="%m/%d/%Y",
        required=True,
    )
    time_format = fields.Selection(
        selection=[
            ("%H:%M:%S", "13:00:00"),
            ("%I:%M:%S %p", " 1:00:00 PM"),
        ],
        default="%H:%M:%S",
        required=True,
    )
    week_start = fields.Selection(
        selection=[
            ("1", "Monday"),
            ("2", "Tuesday"),
            ("3", "Wednesday"),
            ("4", "Thursday"),
            ("5", "Friday"),
            ("6", "Saturday"),
            ("7", "Sunday"),
        ],
        string="First Day of Week",
        default="7",
        required=True,
    )
    grouping = fields.Selection(
        selection=[
            ("[3,0]", "International Grouping"),
            ("[3,2,0]", "Indian Grouping"),
        ],
        string="Separator Format",
        default="[3,0]",
        required=True,
        help="The International Grouping will represent 123456789 to be 123,456,789.00; "
        "The Indian Grouping will represent 123456789 to be 12,34,56,789.00",
    )
    decimal_point = fields.Char(
        string="Decimal Separator",
        trim=False,
        default=".",
        required=True,
    )
    thousands_sep = fields.Char(
        string="Thousands Separator",
        trim=False,
        default=",",
    )

    @api.depends("code", "flag_image")
    def _compute_flag_image_url(self) -> None:
        has_flag = set(self.with_context(bin_size=True).filtered("flag_image")._ids)
        for lang in self:
            if lang.id in has_flag:
                lang.flag_image_url = f"/web/image/res.lang/{lang.id}/flag_image"
            elif not lang.code:
                lang.flag_image_url = False
            else:
                country_code = lang.code.lower().rsplit("_")[-1]
                if country_code.isdigit() or "_" not in lang.code:
                    country_code = lang.code.lower().split("_")[0]
                lang.flag_image_url = (
                    f"/base/static/img/country_flags/{country_code}.png"
                )

    flag_image = fields.Image(string="Image")
    flag_image_url = fields.Char(compute=_compute_flag_image_url)

    _name_uniq = models.Constraint(
        "unique(name)",
        "The name of the language must be unique!",
    )
    _code_uniq = models.Constraint(
        "unique(code)",
        "The code of the language must be unique!",
    )
    _url_code_uniq = models.Constraint(
        "unique(url_code)",
        "The URL code of the language must be unique!",
    )

    @api.constrains("active")
    def _check_active(self) -> None:
        if self.env.registry.ready and not self.search_count(
            [("active", "=", True)], limit=1
        ):
            _debug.logic("active_check_refused", langs=self.mapped("code"))
            raise ValidationError(_("At least one language must be active."))

    @api.constrains("time_format", "date_format")
    def _check_format(self) -> None:
        for lang in self:
            for pattern in lang._disallowed_datetime_patterns:
                if (lang.time_format and pattern in lang.time_format) or (
                    lang.date_format and pattern in lang.date_format
                ):
                    _debug.logic("format_rejected", lang=lang.code, pattern=pattern)
                    raise ValidationError(
                        _(
                            "Invalid date/time format directive specified. "
                            "Please refer to the list of allowed directives, "
                            "displayed when you edit a language."
                        )
                    )

    @api.onchange("time_format", "date_format")
    def _onchange_format(self) -> dict[str, Any] | None:
        warning = {
            "warning": {
                "title": _("Using 24-hour clock format with AM/PM can cause issues."),
                "message": _("Changing to 12-hour clock format instead."),
                "type": "notification",
            }
        }
        for lang in self:
            if (
                lang.date_format
                and "%H" in lang.date_format
                and "%p" in lang.date_format
            ):
                lang.date_format = lang.date_format.replace("%H", "%I")
                _debug.logic("clock_format_fixed", lang=lang.code, field="date_format")
                return warning
            if (
                lang.time_format
                and "%H" in lang.time_format
                and "%p" in lang.time_format
            ):
                lang.time_format = lang.time_format.replace("%H", "%I")
                _debug.logic("clock_format_fixed", lang=lang.code, field="time_format")
                return warning
        return None

    def _register_hook(self) -> None:
        if not self.search_count([], limit=1):
            _logger.error("No language is active.")

    def _get_lang_by_code(self, code: str) -> Self:
        return self.with_context(active_test=False).search([("code", "=", code)])

    def _activate_lang(self, code: str) -> Self:
        lang = self._get_lang_by_code(code)
        if lang and not lang.active:
            _debug.lifecycle("lang_activated", code=code, install=False)
            lang.active = True
        return lang

    def _activate_and_install_lang(self, code: str) -> Self:
        lang = self._get_lang_by_code(code)
        if lang and not lang.active:
            _debug.lifecycle("lang_activated", code=code, install=True)
            lang.action_unarchive()
        return lang

    def _create_lang(self, lang: str, lang_name: str | None = None) -> Self:
        iso_lang = tools.get_iso_codes(lang)
        if not lang_name:
            lang_name = lang

        def fix_datetime_format(format):
            format = format.replace("%-", "%")
            for pattern, replacement in tools.misc.DATETIME_FORMATS_MAP.items():
                format = format.replace(pattern, replacement)
            return str(format)

        with _LOCALE_LOCK:
            try:
                fail = True
                for ln in tools.translate.get_locales(lang):
                    try:
                        locale.setlocale(locale.LC_ALL, str(ln))
                        fail = False
                        break
                    except locale.Error:
                        continue
                if fail:
                    lc = locale.getlocale()[0]
                    msg = "Unable to get information for locale %s. Information from the default locale (%s) have been used."
                    _logger.warning(msg, lang, lc)

                conv = locale.localeconv()
                grouping = str(conv.get("grouping") or "[3,0]").replace(" ", "")
                grouping_options = {v for v, _ in self._fields["grouping"].selection}
                _debug.logic(
                    "locale_resolved",
                    code=lang,
                    locale_found=not fail,
                    grouping=grouping,
                    grouping_known=grouping in grouping_options,
                )
                lang_info = {
                    "code": lang,
                    "iso_code": iso_lang,
                    "name": lang_name,
                    "active": True,
                    "date_format": fix_datetime_format(
                        locale.nl_langinfo(locale.D_FMT)
                    ),
                    "time_format": fix_datetime_format(
                        locale.nl_langinfo(locale.T_FMT)
                    ),
                    "decimal_point": str(conv["decimal_point"]),
                    "thousands_sep": str(conv["thousands_sep"]),
                    "grouping": grouping if grouping in grouping_options else "[3,0]",
                }
            finally:
                tools.translate.resetlocale()
        _debug.lifecycle("lang_created_from_locale", code=lang, iso=iso_lang)
        return self.create(lang_info)

    @api.model
    def install_lang(self) -> bool:
        lang_code = (tools.config.get("load_language") or "en_US").split(",")[0]
        _debug.lifecycle("install_lang", code=lang_code)
        self._activate_lang(lang_code) or self._create_lang(lang_code)
        IrDefault = self.env["ir.default"]
        default_value = IrDefault._get("res.partner", "lang")
        _debug.logic(
            "partner_lang_default",
            code=lang_code,
            existing=default_value,
            set_default=default_value is None,
        )
        if default_value is None:
            IrDefault.set("res.partner", "lang", lang_code)
            partner = self.env.company.partner_id
            if not partner.lang:
                partner.write({"lang": lang_code})
        return True

    CACHED_FIELDS = OrderedSet(
        [
            "id",
            "name",
            "code",
            "iso_code",
            "url_code",
            "active",
            "direction",
            "date_format",
            "time_format",
            "week_start",
            "grouping",
            "decimal_point",
            "thousands_sep",
            "flag_image_url",
        ]
    )

    def _get_data(self, **kwargs) -> LangData:
        if len(kwargs) != 1:
            raise TypeError(
                f"_get_data() requires exactly one keyword argument, got {len(kwargs)}"
            )
        [[field_name, field_value]] = kwargs.items()
        return self._get_active_by_field(field_name)[field_value]

    def _get_lang_cached(self, code: str) -> Self:
        return self.browse(self._get_data(code=code).id)

    def _get_code(self, code: str) -> str | Literal[False]:
        return self._get_data(code=code).code

    @api.model
    @api.readonly
    def get_installed(self) -> list[tuple[str, str]]:
        return [
            (code, data.name)
            for code, data in self._get_active_by_field("code").items()
        ]

    @tools.ormcache("field", cache="stable")
    def _get_active_by_field(self, field: str) -> LangDataDict:
        if field not in self.CACHED_FIELDS:
            _debug.logic("active_by_field_refused", field=field)
            raise UserError(_('Field "%s" is not cached', field))
        if field == "code":
            langs = (
                self.sudo()
                .with_context(active_test=True)
                .search_fetch([], self.CACHED_FIELDS, order="name")
            )
            _debug.perf.count("active_langs_computed", langs=langs.mapped("code"))
            return LangDataDict(
                {
                    lang.code: LangData({f: lang[f] for f in self.CACHED_FIELDS})
                    for lang in langs
                }
            )
        _debug.perf.count("active_langs_reindexed", field=field)
        return LangDataDict(
            {data[field]: data for data in self._get_active_by_field("code").values()}
        )

    def action_unarchive(self) -> bool:
        activated = self.filtered(lambda rec: not rec.active)
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "unarchive", langs=self.mapped("code"), activated=len(activated)
            )
        res = super(ResLang, activated).action_unarchive()
        if activated:
            active_lang = activated.mapped("code")
            mods = self.env["ir.module.module"].search([("state", "=", "installed")])
            with _debug.perf(
                "lang_translations_loaded",
                cr=self.env.cr,
                langs=active_lang,
                modules=len(mods),
            ):
                mods._update_translations(active_lang)
        return res

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        _debug.lifecycle("create", codes=[vals.get("code") for vals in vals_list])
        self.env.registry.clear_cache("stable")
        return super().create(
            [
                vals
                if vals.get("url_code")
                else {**vals, "url_code": vals.get("iso_code") or vals["code"]}
                for vals in vals_list
            ]
        )

    def write(self, vals: dict[str, Any]) -> bool:
        lang_codes = self.mapped("code")
        _debug.lifecycle("write", codes=lang_codes, fields=list(vals))
        if "code" in vals and any(code != vals["code"] for code in lang_codes):
            _debug.logic("write_refused", codes=lang_codes, reason="code_change")
            raise UserError(_("Language code cannot be modified."))
        if "active" in vals and not vals["active"]:
            self._check_deactivation_allowed(lang_codes)
            _debug.lifecycle("partner_lang_defaults_discarded", codes=lang_codes)
            self.env["ir.default"].discard_values("res.partner", "lang", lang_codes)

        res = super().write(vals)

        if vals.get("active"):
            long_langs = self.filtered(lambda lang: "_" in lang.url_code)
            short_codes = {lang.code.split("_")[0] for lang in long_langs}
            _debug.logic(
                "url_code_shortening",
                codes=lang_codes,
                long_langs=len(long_langs),
                short_codes=len(short_codes),
            )
            by_url_code = {}
            if short_codes:
                for candidate in self.with_context(active_test=False).search(
                    [("url_code", "in", list(short_codes))]
                ):
                    by_url_code.setdefault(candidate.url_code, candidate)
            for long_lang in long_langs:
                short_code = long_lang.code.split("_")[0]
                short_lang = by_url_code.get(short_code)
                if (
                    short_lang
                    and short_lang.url_code == short_code
                    and not short_lang.active
                    and short_lang.code != short_code
                ):
                    short_lang.url_code = short_lang.code
                    long_lang.url_code = short_code
                    _debug.logic(
                        "url_code_swapped", long=long_lang.code, short=short_lang.code
                    )

        self.env.flush_all()
        self.env.registry.clear_cache("stable")
        _debug.lifecycle("stable_cache_cleared", by="write", codes=lang_codes)
        if "active" in vals:
            self._reset_environment_languages()
        return res

    _DEACTIVATION_REFUSALS = {
        ("res.users", True): _lt(
            "Cannot deactivate a language that is currently used by users."
        ),
        ("res.users", False): _lt(
            "Cannot deactivate a language that is used by archived users, "
            "such as the ones automated processes run as."
        ),
        ("res.partner", True): _lt(
            "Cannot deactivate a language that is currently used by contacts."
        ),
        ("res.partner", False): _lt(
            "Cannot deactivate a language that is used by archived contacts. "
            "Reactivating those contacts would leave them with an inactive language."
        ),
    }

    def _check_deactivation_allowed(self, lang_codes: list[str]) -> None:
        # one query per model, the first row by `active desc` telling whether
        # an active holder exists; the message ranks users over contacts and
        # active over archived
        holders = {
            model_name: self.env[model_name]
            .with_context(active_test=False)
            .search_fetch(
                [("lang", "in", lang_codes)],
                ["active"],
                order="active desc, id",
                limit=1,
            )
            for model_name in ("res.users", "res.partner")
        }
        for active in (True, False):
            for model_name, holder in holders.items():
                if holder and holder.active == active:
                    _debug.logic(
                        "deactivate_refused",
                        codes=lang_codes,
                        model=model_name,
                        active=active,
                    )
                    raise UserError(
                        str(self._DEACTIVATION_REFUSALS[model_name, active])
                    )

    def _reset_environment_languages(self) -> None:
        # Environment.lang caches whether its context language is installed;
        # the transaction keeps recent environments alive, so a toggled
        # language must not be answered from that cache
        envs = list(self.env.transaction.envs)
        _debug.lifecycle("environment_languages_reset", envs=len(envs))
        for env in envs:
            reset_cached_properties(env)

    @api.ondelete(at_uninstall=True)
    def _unlink_except_default_lang(self) -> None:
        for language in self:
            if language.code == "en_US":
                _debug.logic("unlink_refused", lang=language.code, reason="base")
                raise UserError(_("Base Language 'en_US' can not be deleted."))
            ctx_lang = self.env.context.get("lang")
            if ctx_lang and (language.code == ctx_lang):
                _debug.logic(
                    "unlink_refused", lang=language.code, reason="user_preferred"
                )
                raise UserError(
                    _(
                        "You cannot delete the language which is the user's preferred language."
                    )
                )
            if language.active:
                _debug.logic("unlink_refused", lang=language.code, reason="active")
                raise UserError(
                    _(
                        "You cannot delete the language which is Active!\nPlease de-activate the language first."
                    )
                )

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", codes=self.mapped("code"))
        self.env.registry.clear_cache("stable")
        self._reset_environment_languages()
        return super().unlink()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for record, vals in zip(self, vals_list, strict=True):
            if "name" not in default:
                vals["name"] = _("%s (copy)", record.name)
            if "code" not in default:
                vals["code"] = self._get_unique_copy_value("code", record.code)
            if "url_code" not in default:
                vals["url_code"] = self._get_unique_copy_value(
                    "url_code", record.url_code
                )
        return vals_list

    def _get_unique_copy_value(self, fname: str, value: str) -> str:
        Lang = self.with_context(active_test=False)
        candidate = f"{value}_copy"
        counter = 2
        while Lang.search_count([(fname, "=", candidate)], limit=1):
            candidate = f"{value}_copy{counter}"
            counter += 1
        _debug.perf.count(
            "unique_copy_value", field=fname, probes=counter - 1, candidate=candidate
        )
        return candidate

    def format(self, percent: str, value, grouping: bool = False) -> str:
        self.check_singleton()
        data = self._get_data(id=self.id)
        if not data:
            _debug.logic("format_refused", lang=self.code, reason="not_installed")
            raise UserError(_("The language %s is not installed.", self.name))
        return format_number(percent, value, data, grouping=grouping)

    def action_activate_langs(self) -> dict[str, Any]:
        self.action_unarchive()
        message = _(
            "The languages that you selected have been successfully installed. Users can choose their favorite language in their preferences."
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "target": "new",
            "params": {
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
