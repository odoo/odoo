import contextlib
from importlib import import_module
from inspect import getmembers, isclass, isfunction, ismodule

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import get_flag

_debug = DebugLog(__name__)


def _flag(country_code):
    with contextlib.suppress(ValueError):
        return get_flag(country_code)
    return ""


def _template_country_code(code, country=""):
    return country or code.split("_")[0] if country is not None else None


def templ(countries, code, name=None, country="", **kwargs):
    country = countries.get(_template_country_code(code, country))
    country_name = f"{_flag(country.code)} {country.name}".strip() if country else ""
    return {
        "name": (
            country_name and (f"{country_name} - {name}" if name else country_name)
        )
        or name,
        "country_id": country and country.id,
        "country_code": country and country.code,
        **kwargs,
    }


def template_module(m):
    return ismodule(m) and m.__name__.split(".")[-1].startswith("template_")


template_class = isclass


def template_function(f):
    return (
        isfunction(f)
        and hasattr(f, "_l10n_template")
        and f._l10n_template[1] == "template_data"
    )


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    account_templates = fields.Binary(
        compute="_compute_account_templates",
        exportable=False,
    )

    @api.depends("state", "category_id")
    @_debug.perf.timed
    def _compute_account_templates(self):
        chart_category = self.env.ref(
            "base.module_category_accounting_localizations_account_charts",
            raise_if_not_found=False,
        )
        ChartTemplate = self.env["account.chart.template"]
        templates_by_module = {}
        for module in self:
            templates = {}
            if module.category_id == chart_category or module.name == "account":
                try:
                    python_module = import_module(f"odoo.addons.{module.name}.models")
                except ModuleNotFoundError:
                    _debug.logic("template_models_missing", module_name=module.name)
                    templates = {}
                else:
                    templates = {
                        fct._l10n_template[0]: {
                            "name": template_values.get("name"),
                            "parent": template_values.get("parent"),
                            "sequence": template_values.get("sequence", 1),
                            "country": template_values.get("country", ""),
                            "visible": template_values.get("visible", True),
                            "installed": module.state == "installed",
                            "module": module.name,
                        }
                        for _name, mdl in getmembers(python_module, template_module)
                        for _name, cls in getmembers(mdl, template_class)
                        for _name, fct in getmembers(cls, template_function)
                        if (template_values := fct(ChartTemplate))
                    }

            templates_by_module[module] = templates

        # one lookup for every template's country instead of an env.ref and a
        # record fetch per template (three queries each, ~120 templates)
        countries = self._get_template_countries(
            {
                _template_country_code(code, vals.get("country", ""))
                for templates in templates_by_module.values()
                for code, vals in templates.items()
            }
        )
        for module, templates in templates_by_module.items():
            module.account_templates = {
                code: templ(countries, code, **vals)
                for code, vals in sorted(
                    templates.items(), key=lambda kv: kv[1]["sequence"]
                )
            }
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "account_templates_computed",
                modules=len(self),
                declaring=sum(1 for module in self if module.account_templates),
                templates=sum(len(module.account_templates or ()) for module in self),
            )

    def _get_template_countries(self, country_codes):
        country_codes.discard(None)
        if not country_codes:
            return {}
        xmlids = (
            self.env["ir.model.data"]
            .sudo()
            .search_fetch(
                [
                    ("module", "=", "base"),
                    ("model", "=", "res.country"),
                    ("name", "in", list(country_codes)),
                ],
                ["name", "res_id"],
            )
        )
        countries = self.env["res.country"].browse(xmlids.mapped("res_id"))
        countries.fetch(["code", "name"])
        by_id = {country.id: country for country in countries}
        return {
            xmlid.name: by_id[xmlid.res_id] for xmlid in xmlids if xmlid.res_id in by_id
        }

    def _account_template_to_auto_install(self):
        company_country_id = self.env.company.country_id.id
        return next(
            (
                tname
                for tname, tvals in self.account_templates.items()
                if tvals.get("visible", True)
                and (
                    (company_country_id and tvals["country_id"] == company_country_id)
                    or tname == "generic_coa"
                )
            ),
            None,
        )

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        was_installed = len(self) == 1 and self.state in (
            "installed",
            "to upgrade",
            "to remove",
        )
        res = super().write(vals)
        is_installed = len(self) == 1 and self.state == "installed"
        if (
            not was_installed
            and is_installed
            and not self.env.company.account_config_id.chart_template
            and self.account_templates
            and (guessed := self._account_template_to_auto_install())
        ):

            def try_loading(env):
                env["account.chart.template"].try_loading(
                    guessed,
                    env.company,
                )

            self.env.registry._auto_install_template = try_loading
        return res

    @_debug.perf.timed
    def _load_module_terms(self, modules, langs, overwrite=False):
        super()._load_module_terms(modules, langs, overwrite=overwrite)
        if "account" in modules:

            def load_account_translations(env):
                env["account.chart.template"]._load_translations(langs=langs)
                env["account.account.tag"]._translate_tax_tags(langs=langs)

            if self.env.registry.loaded:
                load_account_translations(self.env)
            else:
                self.env.registry._delayed_account_translator = (
                    load_account_translations
                )

    @_debug.perf.timed
    def _register_hook(self):
        _debug.lifecycle("_register_hook", records=self)
        super()._register_hook()
        if hasattr(self.env.registry, "_delayed_account_translator"):
            self.env.registry._delayed_account_translator(self.env)
            del self.env.registry._delayed_account_translator
        if hasattr(self.env.registry, "_auto_install_template"):
            self.env.registry._auto_install_template(self.env)
            del self.env.registry._auto_install_template

    def module_uninstall(self):
        unlinked_templates = [
            code for template in self.mapped("account_templates") for code in template
        ]
        if unlinked_templates:
            companies = self.env["res.company"].search(
                [
                    ("account_config_id.chart_template", "in", unlinked_templates),
                ]
            )
            companies.account_config_id.chart_template = False
            companies.flush_recordset()

        return super().module_uninstall()
