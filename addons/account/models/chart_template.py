import ast
import csv
import logging
import re
from collections import defaultdict, deque
from copy import deepcopy
from functools import wraps
from inspect import getmembers

from odoo import Command, api, models
from odoo.exceptions import AccessError, RedirectWarning, UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.modules import get_resource_from_path
from odoo.tools import SQL, file_open, float_compare, get_lang
from odoo.tools.translate import TranslationImporter, _, code_translations

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)

TEMPLATE_MODELS = (
    "account.group",
    "account.account",
    "account.fiscal.position",
    "account.tax.group",
    "account.tax",
    "account.journal",
    "account.reconcile.model",
)

REPARTITION_LINE_FIELDS = (
    "repartition_line_ids",
    "invoice_repartition_line_ids",
    "refund_repartition_line_ids",
)

TEMPLATE_MODELS_REMOVAL_ORDER = ("account.move", *reversed(TEMPLATE_MODELS))

TAX_TAG_DELIMITER = "||"

SYSCOHADA_LIST = [
    "BJ",
    "BF",
    "CM",
    "CF",
    "KM",
    "CG",
    "CI",
    "GA",
    "GN",
    "GW",
    "GQ",
    "ML",
    "NE",
    "CD",
    "SN",
    "TD",
    "TG",
]


def get_python_translation(module, lang, value):
    value_translated = code_translations.get_python_translations(module, lang).get(
        value
    )
    if not value_translated:
        value_translated = code_translations.get_python_translations(
            module, lang.split("_")[0]
        ).get(value)
    return value_translated


def preserve_existing_tags_on_taxes(env, module):
    xml_records = env["ir.model.data"].search(
        [("model", "=", "account.account.tag"), ("module", "=", module)]
    )
    if xml_records:
        env.cr.execute(
            "update ir_model_data set noupdate = 't' where id = ANY(%s)",
            [list(xml_records.ids)],
        )
        _debug.perf.count("tag_xmlids_noupdated", rows=env.cr.rowcount)


def template(template=None, model="template_data"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if template is not None:
                args, kwargs = args[:1], {}
            return func(*args, **kwargs)

        path = func.__globals__["__file__"]
        path_info = get_resource_from_path(path)
        module = path_info.module if path_info else "account"

        wrapper._module = module
        wrapper._l10n_template = (template, model)
        return wrapper

    return decorator


class AccountChartTemplate(models.AbstractModel):
    _name = "account.chart.template"
    _description = "Account Chart Template"

    @property
    def _template_register(self):
        def is_template(func):
            return callable(func) and hasattr(func, "_l10n_template")

        template_register = defaultdict(lambda: defaultdict(list))
        cls = self.env.registry[self._name]
        for _attr, func in getmembers(cls, is_template):
            template, model = func._l10n_template
            template_register[template][model].append(func)
        cls._template_register = template_register
        return template_register

    @_debug.perf.timed
    def _post_model_setup__(self):
        _debug.lifecycle("_post_model_setup_", records=self)
        super()._post_model_setup__()
        self.env.registry[
            self._name
        ]._template_register = AccountChartTemplate._template_register

    def _get_chart_template_mapping(self, get_all=False):
        chart_category = self.env.ref(
            "base.module_category_accounting_localizations_account_charts",
            raise_if_not_found=False,
        )
        declares_a_template = Domain("name", "=", "account")
        if chart_category:
            declares_a_template |= Domain("category_id", "=", chart_category.id)
        modules = (
            self.env["ir.module.module"]
            .sudo()
            .search(Domain("state", "!=", "uninstallable") & declares_a_template)
        )

        return {
            name: template
            for mapping in modules.mapped("account_templates")
            for name, template in mapping.items()
            if get_all or template["visible"]
        }

    def _select_chart_template(self, country=None):
        country = country if country is not None else self.env.company.country_id
        chart_template_mapping = self._get_chart_template_mapping()
        return [
            (template_code, template["name"])
            for template_code, template in sorted(
                chart_template_mapping.items(),
                key=lambda t: (
                    bool(country) and t[1]["country_id"] != country.id,
                    t[0] != "generic_coa",
                ),
            )
        ]

    def _guess_chart_template(self, country):
        return self._select_chart_template(country)[0][0]

    @_debug.perf.timed
    def try_loading(
        self, template_code, company, install_demo=False, force_create=True
    ):
        _debug.lifecycle("try_loading", records=self)
        if not company:
            return None
        if isinstance(company, int):
            company = self.env["res.company"].browse([company])
        if (
            not self.env.registry.loaded
            and not install_demo
            and not hasattr(self.env.registry, "_auto_install_template")
        ):
            _logger.warning(
                "Incorrect usage of try_loading without a fully loaded registry. This could lead to issues. (%s-%s)",
                company.name,
                template_code,
            )
        template_code = template_code or self._guess_chart_template(company.country_id)
        _debug.pipeline(
            "try_loading",
            chart=template_code,
            company=company,
            demo=install_demo,
            force_create=force_create,
            current=company.account_config_id.chart_template,
        )

        mapping = self._get_chart_template_mapping(get_all=True).get(template_code, {})
        if (
            not mapping.get("visible", True)
            and template_code != company.account_config_id.chart_template
        ):
            raise UserError(
                _(
                    "The %s chart template shouldn't be selected directly. Instead, you should directly select the chart template related to your country.",
                    template_code,
                )
            )

        return self._load(template_code, company, install_demo, force_create)

    def _get_company_records(self, model, company_field, company):
        return (
            self.env[model]
            .sudo()
            .with_context(active_test=False)
            .search([(company_field, "child_of", company.id)])
        )

    def _remove_existing_accounting_data(self, company):
        children_companies = self.env["res.company"].search(
            [("id", "child_of", company.id)]
        )
        for model in TEMPLATE_MODELS_REMOVAL_ORDER:
            company_field = self._template_company_field(model)
            records = self._get_company_records(model, company_field, company)
            if company_field == "company_ids":
                records_to_keep = records.filtered(
                    lambda r: r.company_ids - children_companies
                )
                records -= records_to_keep
                for records_for_companies in records_to_keep.grouped(
                    "company_ids"
                ).values():
                    records_for_companies.company_ids -= children_companies
            records.with_context({MODULE_UNINSTALL_FLAG: True}).unlink()

    @_debug.perf.timed
    def _load(self, template_code, company, install_demo, force_create=True):
        _debug.lifecycle("_load", records=self)
        if not self.env.is_system():
            raise AccessError(_("Only administrators can install chart templates"))
        self = self.sudo()
        chart_template_mapping = self._get_chart_template_mapping(get_all=True).get(
            template_code
        )
        if chart_template_mapping is None:
            raise UserError(
                _("No chart template is declared under the code %s.", template_code)
            )
        if not company.country_id:
            company.country_id = chart_template_mapping.get("country_id")

        module_name = chart_template_mapping.get("module")
        module = self.env["ir.module.module"].search(
            [("name", "=", module_name), ("state", "=", "uninstalled")]
        )
        if module:
            _debug.pipeline(
                "installing_l10n_module_first",
                chart=template_code,
                module_name=module_name,
            )
            module.button_immediate_install()
            self.env.transaction.reset()
            self = self.env()["account.chart.template"]
        original_context_lang = self.env.context.get("lang")
        self = self.with_context(
            default_company_id=company.id,
            allowed_company_ids=[company.id],
            tracking_disable=True,
            delay_account_group_sync=True,
            lang="en_US",
            chart_template_load=True,
        )
        company = self.env["res.company"].browse(company.id)

        reload_template = template_code == company.account_config_id.chart_template
        company.account_config_id.chart_template = template_code

        if (
            not reload_template
            and not company.parent_id
            and (not company.root_id._existing_accounting() or install_demo)
        ):
            _debug.logic(
                "removing_existing_accounting_data",
                chart=template_code,
                company=company,
            )
            self._remove_existing_accounting_data(company)
        _debug.logic(
            "_load",
            chart=template_code,
            reload=reload_template,
            branch=bool(company.parent_id),
        )

        data = self._prepare_chart_template_data(template_code)
        template_data = data.pop("template_data")
        self._split_company_config_data(company, data)
        if company.parent_id:
            data = {
                "res.company": data["res.company"],
                "account.config": data["account.config"],
            }

        if reload_template:
            self._pre_reload_data(company, template_data, data, force_create)
            install_demo = False
        data = self._pre_load_data(template_code, company, template_data, data)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "loading",
                chart=template_code,
                loading={model: len(recs) for model, recs in data.items()},
            )
        created_records = self._load_data(data)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "loaded",
                chart=template_code,
                loaded={m: len(r) for m, r in created_records.items()},
            )
        self._post_load_data(template_code, company, template_data)
        self._load_translations(companies=company)

        AccountGroup = self.env["account.group"].with_context(
            delay_account_group_sync=False
        )
        AccountGroup._adapt_parent_account_group(company=company)

        if install_demo and not reload_template:
            try:
                with self.env.cr.savepoint():
                    self = self.with_context(lang=original_context_lang)
                    self._install_demo(company.with_env(self.env))
            except Exception:
                _logger.exception("Error while loading accounting demo data")
        for subsidiary in company.child_ids:
            self._load(template_code, subsidiary, install_demo, force_create)

        return created_records

    @api.model
    def _install_demo(self, companies):
        if not isinstance(companies, models.BaseModel):
            companies = self.env["res.company"].browse(companies)
        for company in companies:
            self.with_context(install_mode=True).sudo().with_context(
                skip_pdf_attachment_generation=True
            )._load_data(self._prepare_demo_data(company))
            self.with_context(install_mode=True)._post_load_demo_data(company)

    @_debug.perf.timed
    def _get_pre_reload_skips(
        self,
        company,
        template_data,
        data,
        xmlid2records,
        current_taxes,
        unique_tax_name_keys,
        obsolete_xmlid,
        force_create,
    ):
        skip_update = set()
        for model_name, records in data.items():
            for xmlid, values in records.items():
                if model_name == "account.fiscal.position":
                    skip = self._pre_reload_fiscal_position(
                        xmlid, values, xmlid2records, force_create
                    )
                elif model_name == "account.tax.group":
                    skip = self._pre_reload_tax_group(
                        xmlid, values, xmlid2records, force_create
                    )
                elif model_name == "account.tax":
                    skip = self._pre_reload_tax(
                        xmlid,
                        values,
                        xmlid2records,
                        current_taxes,
                        unique_tax_name_keys,
                        obsolete_xmlid,
                        force_create,
                    )
                elif model_name == "account.account":
                    skip = self._pre_reload_account(
                        company,
                        template_data,
                        data,
                        xmlid,
                        values,
                        xmlid2records,
                        force_create,
                    )
                else:
                    continue
                if skip:
                    skip_update.add((model_name, xmlid))
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "reload_skips_by_model",
                company=company,
                force_create=force_create,
                templates={model: len(recs) for model, recs in data.items()},
                skipped={
                    model: sum(
                        1 for skip_model, _x in skip_update if skip_model == model
                    )
                    for model in data
                },
                obsolete=len(obsolete_xmlid),
            )
        return skip_update

    @_debug.perf.timed
    def _pre_reload_data(self, company, template_data, data, force_create=True):
        for prop, model in self._get_property_accounts().items():
            if model == "res.company":
                is_set = bool(company[prop])
            else:
                is_set = self.env["ir.default"]._get(model, prop, company_id=company.id)
            if is_set:
                template_data.pop(prop, None)
        data.pop("account.reconcile.model", None)
        config = company.account_config_id
        for record, model_data in (
            (company, data.get("res.company", {})),
            (config, data.get("account.config", {})),
        ):
            if record.id not in model_data:
                continue
            record_vals = model_data[record.id]
            for fname in list(record_vals):
                field = record._fields.get(fname)
                if not field or field.type != "many2one" or record[fname]:
                    del record_vals[fname]
        if config.id in data.get("account.config", {}):
            data["account.config"][config.id]["anglo_saxon_accounting"] = (
                config.anglo_saxon_accounting
            )
        self._pre_reload_journals(company, data)
        if self.env["account.group"].search_count(
            [] if company.parent_id else [("company_id", "=", company.id)],
            limit=1,
        ):
            data.pop("account.group", None)

        current_taxes = self._reload_existing_records(company, "account.tax")
        xmlid2records = {"account.tax": self._reload_xmlid_mapping(current_taxes)}
        for model in (
            "account.fiscal.position",
            "account.tax.group",
            "account.account",
        ):
            xmlid2records[model] = self._reload_xmlid_mapping(
                self._reload_existing_records(company, model)
            )
        unique_tax_name_keys = set(current_taxes.mapped(self._unique_tax_name_key))

        obsolete_xmlid = set()
        skip_update = self._get_pre_reload_skips(
            company,
            template_data,
            data,
            xmlid2records,
            current_taxes,
            unique_tax_name_keys,
            obsolete_xmlid,
            force_create,
        )

        if _debug.logic.enabled:
            _debug.logic(
                "chart_reload_skips",
                company=company,
                skip_count=len(skip_update),
                skipped=sorted(skip_update)[:8],
                obsolete_count=len(obsolete_xmlid),
                obsolete=sorted(obsolete_xmlid)[:8],
            )
        for skip_model, skip_xmlid in skip_update:
            data[skip_model].pop(skip_xmlid, None)

        if obsolete_xmlid:
            self.env["ir.model.data"].search(
                [
                    (
                        "name",
                        "in",
                        [f"{company.id}_{xmlid}" for xmlid in obsolete_xmlid],
                    ),
                    ("module", "=", "account"),
                ]
            ).unlink()

        self._pre_reload_creates_into_updates(data)

    def _reload_existing_records(self, company, model):
        return (
            self.env[model]
            .with_context(active_test=False)
            .search([*self.env[model]._check_company_domain(company)])
        )

    def _reload_xmlid_mapping(self, records):
        company_xmlid_re = re.compile(r"account\.\d+_(?P<template_xmlid>.+)")
        matches = (
            (record, company_xmlid_re.fullmatch(xml_id))
            for record, xml_id in records.get_external_id().items()
        )
        return {
            match["template_xmlid"]: records.browse(record).with_prefetch(
                records._prefetch_ids
            )
            for record, match in matches
            if match
        }

    @_debug.perf.timed
    def _pre_reload_journals(self, company, data):
        lang = self._get_untranslatable_fields_target_language(
            company.account_config_id.chart_template, company
        )
        Journal = self.env["account.journal"].with_context(active_test=False)
        company_domain = self.env["account.journal"]._check_company_domain(company)
        existing_journals = Journal.search(company_domain)
        _debug.pipeline(
            "journals_reload_matching",
            company=company,
            lang=lang,
            existing=len(existing_journals),
            templates=len(data.get("account.journal", {})),
        )
        for xmlid, journal_data in list(data.get("account.journal", {}).items()):
            if self.ref(xmlid, raise_if_not_found=False):
                _debug.logic("journal_xmlid_exists", company=company, xmlid=xmlid)
                del data["account.journal"][xmlid]
                continue
            journal = None
            if "code" in journal_data:
                code = (
                    self._get_field_translation(journal_data, "code", lang)
                    or journal_data["code"]
                )
                journal = existing_journals.filtered(
                    lambda j, code=code: j.code == code
                )
            if not journal and "name" in journal_data and "type" in journal_data:
                translated_name = self._get_field_translation(
                    journal_data, "name", lang
                )
                journal = existing_journals.filtered(
                    lambda j, journal_data=journal_data, translated_name=translated_name: (
                        j.type == journal_data["type"]
                        and j.name in (journal_data["name"], translated_name)
                    )
                )[:1]
            _debug.logic(
                "journal_matched_existing",
                company=company,
                xmlid=xmlid,
                journal=journal,
                by_code="code" in journal_data,
            )
            if journal:
                del data["account.journal"][xmlid]
                self.env["ir.model.data"]._update_xmlids(
                    [
                        {
                            "xml_id": self.company_xmlid(xmlid, company),
                            "record": journal,
                            "noupdate": True,
                        }
                    ]
                )

    def _pre_reload_fiscal_position(self, xmlid, values, xmlid2records, force_create):
        if xmlid not in xmlid2records["account.fiscal.position"]:
            return not force_create
        old_ids = values.pop("account_ids", [])
        if not force_create:
            old_ids = []
        new_ids = [
            element
            for element in old_ids
            if self._reload_account_mapping_is_new(element)
        ]
        if new_ids:
            values["account_ids"] = new_ids
        return False

    def _reload_account_mapping_is_new(self, element):
        match element:
            case Command.CREATE, _, {
                "account_src_id": src_id,
                "account_dest_id": dest_id,
            }:
                return not self.ref(src_id, raise_if_not_found=False) or (
                    dest_id and not self.ref(dest_id, raise_if_not_found=False)
                )
        return False

    def _pre_reload_tax_group(self, xmlid, values, xmlid2records, force_create):
        if xmlid not in xmlid2records["account.tax.group"]:
            return not force_create
        for field_name in ("tax_payable_account_id", "tax_receivable_account_id"):
            if field_name in values and self.ref(
                values[field_name], raise_if_not_found=False
            ):
                values.pop(field_name, None)
        return False

    def _unique_tax_name_key(self, tax):
        return (
            tax.name,
            tax.type_tax_use,
            tax.tax_scope,
            tax.country_id,
            frozenset(tax.company_ids.root_id.ids),
        )

    def _reload_tax_template_changed(self, tax, template):
        template_line_ids = [
            x for x in template.get("repartition_line_ids", []) if x[0] != Command.CLEAR
        ]
        return (
            tax.amount_type != template.get("amount_type", "percent")
            or float_compare(tax.amount, template.get("amount", 0), precision_digits=4)
            != 0
            or len(template_line_ids) not in (0, len(tax.repartition_line_ids))
        )

    @_debug.perf.timed
    def _pre_reload_tax(
        self,
        xmlid,
        values,
        xmlid2records,
        current_taxes,
        unique_tax_name_keys,
        obsolete_xmlid,
        force_create,
    ):
        xmlid2tax = xmlid2records["account.tax"]
        if xmlid in xmlid2tax and not self._reload_tax_template_changed(
            xmlid2tax[xmlid], values
        ):
            _debug.logic("tax_unchanged_relinked", xmlid=xmlid)
            self._pre_reload_tax_relink(values, xmlid2records, force_create)
            return False
        if not force_create:
            _debug.logic(
                "tax_skipped", xmlid=xmlid, reason="changed_or_new_without_force"
            )
            return True
        if self.env.context.get("force_new_tax_active"):
            values["active"] = True
        if xmlid in xmlid2tax:
            obsolete_xmlid.add(xmlid)
            oldtax = xmlid2tax[xmlid]
        else:
            oldtax = current_taxes.filtered(
                lambda t, values=values: (
                    t.name == values.get("name")
                    and t.type_tax_use == values.get("type_tax_use")
                    and t.tax_scope == values.get("tax_scope", False)
                )
            )
        _debug.logic(
            "tax_superseded",
            xmlid=xmlid,
            obsolete_xmlid=xmlid in xmlid2tax,
            oldtax=oldtax,
        )
        self._reload_rename_superseded_taxes(oldtax, unique_tax_name_keys)
        return False

    def _reload_rename_superseded_taxes(self, oldtax, unique_tax_name_keys):
        if not oldtax:
            return
        uniq_key = self._unique_tax_name_key(oldtax[:1])
        pattern = rf"^(?:\[old\d*\] |){re.escape(str(uniq_key[0]))}$"
        matching_names = sum(
            1
            for key in unique_tax_name_keys
            if re.match(pattern, key[0]) and key[1:] == uniq_key[1:]
        )
        _debug.logic(
            "superseded_taxes_renamed", taxes=oldtax, matching_names=matching_names
        )
        for index, tax_to_rename in enumerate(oldtax):
            rename_idx = index + matching_names
            if rename_idx:
                suffix = rename_idx - 1 if rename_idx > 1 else ""
                tax_to_rename.name = f"[old{suffix}] {tax_to_rename.name}"
                unique_tax_name_keys.add(self._unique_tax_name_key(tax_to_rename))

    @_debug.perf.timed
    def _pre_reload_tax_relink(self, values, xmlid2records, force_create):
        fiscal_position_ids = values.get("fiscal_position_ids")
        original_tax_ids = values.get("original_tax_ids")
        repartition_lines = values.get("repartition_line_ids")
        values.clear()
        if fiscal_position_ids:
            link_commands = [
                Command.link(xml_id)
                for xml_id in fiscal_position_ids.split(",")
                if force_create or xml_id in xmlid2records["account.fiscal.position"]
            ]
            if link_commands:
                values["fiscal_position_ids"] = link_commands
        if (
            force_create
            and original_tax_ids
            and (
                new_taxes := [
                    xml_id
                    for xml_id in original_tax_ids.split(",")
                    if xml_id not in xmlid2records["account.tax"]
                ]
            )
        ):
            values["original_tax_ids"] = [
                Command.link(alt_xml_id) for alt_xml_id in new_taxes
            ]
        if repartition_lines:
            values["repartition_line_ids"] = repartition_lines
            for element in repartition_lines:
                match element:
                    case int() as command, _, {
                        "tag_ids": tags
                    } as repartition_line_values if command in tuple(Command):
                        repartition_line_values.clear()
                        repartition_line_values["tag_ids"] = tags or [Command.clear()]
        if _debug.logic.enabled:
            _debug.logic(
                "tax_relink_kept",
                force_create=force_create,
                kept=sorted(values),
                fiscal_positions=len(values.get("fiscal_position_ids", ())),
                new_original_taxes=len(values.get("original_tax_ids", ())),
            )

    def _pre_reload_account(
        self, company, template_data, data, xmlid, values, xmlid2records, force_create
    ):
        if not self._reload_account_points_at_an_existing_one(
            company, template_data, xmlid, values, xmlid2records["account.account"]
        ):
            return not force_create
        if "tag_ids" in values:
            data["account.account"][xmlid] = {"tag_ids": values["tag_ids"]}
            return False
        return True

    def _pre_reload_creates_into_updates(self, data):
        for model_name, records in data.items():
            _fields = self.env[model_name]._fields
            for xmlid, values in records.items():
                x2manyfields = [
                    fname
                    for fname in values
                    if fname in _fields
                    and _fields[fname].type in ("one2many", "many2many")
                    and isinstance(values[fname], (list, tuple))
                ]
                if not x2manyfields:
                    continue
                if isinstance(xmlid, int):
                    rec = self.env[model_name].browse(xmlid).exists()
                else:
                    rec = self.ref(xmlid, raise_if_not_found=False)
                if not rec:
                    continue
                for fname in x2manyfields:
                    for i, (line, (command, _id, vals)) in enumerate(
                        zip(rec[fname], values[fname], strict=False)
                    ):
                        if command == Command.CREATE:
                            values[fname][i] = Command.update(line.id, vals)
            _debug.pipeline(
                "x2many_creates_checked", model=model_name, records=len(records)
            )

    @_debug.perf.timed
    def _reload_account_points_at_an_existing_one(
        self, company, template_data, xmlid, values, xmlid2account
    ):
        values.pop("reconcile", None)
        account = xmlid2account.get(xmlid)
        code_digits = int(template_data.get("code_digits", 6))
        normalized_code = f"{values['code']:<0{code_digits}}"
        escaped_code_re = re.escape(values["code"])
        escaped_code_sql = re.sub(r"([^a-zA-Z0-9])", r"\\\1", values["code"])
        if account and re.match(f"^{escaped_code_re}0*$", account.code):
            _debug.logic(
                "account_xmlid_code_matches",
                company=company,
                xmlid=xmlid,
                code=values.get("code"),
                account=account,
            )
            return True

        query = self.env["account.account"]._search(
            self.env["account.account"]._check_company_domain(company)
        )
        account_code = (
            self.with_company(company)
            .env["account.account"]
            ._field_to_sql("account_account", "code", query)
        )
        query.add_where(SQL("%s SIMILAR TO %s", account_code, f"{escaped_code_sql}0*"))
        accounts = self.env["account.account"].browse(query)
        if not accounts:
            _debug.logic(
                "account_code_unmatched",
                company=company,
                xmlid=xmlid,
                code=values.get("code"),
                has_xmlid_account=bool(account),
            )
            return bool(account)
        existing_account = accounts.sorted(key=lambda x: x.code != normalized_code)[0]
        _debug.logic(
            "account_code_relinked",
            company=company,
            xmlid=xmlid,
            normalized_code=normalized_code,
            candidates=accounts,
            account=existing_account,
        )
        self.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": self.company_xmlid(xmlid, company),
                    "record": existing_account,
                    "noupdate": True,
                }
            ]
        )
        return True

    def _split_company_config_data(self, company, data):
        # a template describes a company's accounting as one dict; the
        # keys the company does not carry are its account.config's
        config = company.account_config_id
        company_data = data.get("res.company", {}).get(company.id, {})
        if "account.config" not in data:
            # loaded right after the company, before the journals and taxes
            # that read its prefixes and fiscal country
            ordered = {}
            for model, records in data.items():
                ordered[model] = records
                if model == "res.company":
                    ordered["account.config"] = {}
            if "account.config" not in ordered:
                ordered["account.config"] = {}
            data.clear()
            data.update(ordered)
        config_data = data["account.config"].setdefault(config.id, {})
        for key in list(company_data):
            base_key = key.split("@")[0]
            if base_key in company._fields or base_key == "__translation_module__":
                continue
            if base_key in config._fields:
                config_data[key] = company_data.pop(key)

    def _pre_load_account_config_vals(self, company, template_data):
        config = company.account_config_id
        vals = {
            key: val
            for key, val in template_data.items()
            if key in config._fields and key not in company._fields
        }
        vals.setdefault("anglo_saxon_accounting", False)
        return vals

    def _pre_load_company_vals(self, company, template_data, fiscal_country):
        property_accounts = self._get_property_accounts()
        vals = {
            key: val
            for key, val in template_data.items()
            if key in company._fields and key != "name" and key not in property_accounts
        }
        if not company.root_id._existing_accounting():
            vals["currency_id"] = (
                company.parent_id.currency_id.id
                if company.parent_id
                else fiscal_country.currency_id.id
            )
        if not company.country_id:
            vals["country_id"] = fiscal_country.id
        if _debug.logic.enabled:
            _debug.logic(
                "company_vals_prepared",
                company=company,
                keys=sorted(vals),
                currency_set="currency_id" in vals,
                country_set="country_id" in vals,
            )
        return vals

    def _pre_load_report_config_vals(self, company, template_data):
        # a template's report layout and paper format are the company's
        # report configuration, not the company
        config = company.report_config_id
        vals = {}
        for key, value in template_data.items():
            field = config._fields.get(key)
            if field is None or key in company._fields or key == "company_id":
                continue
            if field.is_many2one and isinstance(value, str):
                value = self.ref(value).id
            vals[key] = value
        if vals:
            _debug.logic(
                "report_config_loaded", company=company.id, fields=sorted(vals)
            )
            config.write(vals)

    def _pre_load_drop_unknown_fields(self, data):
        for model_name, records in data.items():
            model_fields = self.env[model_name]._fields
            for record in records.values():
                for key in [
                    key
                    for key in record
                    if key != "__translation_module__"
                    and key.split("@")[0] not in model_fields
                ]:
                    del record[key]

    def _pre_load_translate_untranslatable(self, template_code, company, data):
        untranslatable_model_fields = self._get_untranslatable_fields_to_translate()
        target_lang = self._get_untranslatable_fields_target_language(
            template_code, company
        )
        _debug.logic(
            "untranslatable_target_lang",
            chart=template_code,
            company=company,
            lang=target_lang,
            models=len(untranslatable_model_fields),
        )
        for model_name, records in data.items():
            untranslatable_fields = untranslatable_model_fields.get(model_name, [])
            for record in records.values():
                for field in untranslatable_fields:
                    if field not in record:
                        continue
                    translation = self._get_field_translation(
                        record, field, target_lang
                    )
                    if translation:
                        record[field] = translation

    @_debug.perf.timed
    def _pre_load_data(self, template_code, company, template_data, data):
        _debug.lifecycle("_pre_load_data", records=self)
        config = company.account_config_id
        config_data = data.get("account.config", {}).get(config.id, {})
        fiscal_country = (
            self.ref(config_data["account_fiscal_country_id"])
            if "account_fiscal_country_id" in config_data
            else config.account_fiscal_country_id
        )
        company.write(
            self._pre_load_company_vals(company, template_data, fiscal_country)
        )
        config.write(self._pre_load_account_config_vals(company, template_data))
        self._pre_load_report_config_vals(company, template_data)

        code_digits = int(template_data.get("code_digits", 6))
        for account_data in data.get("account.account", {}).values():
            if "code" in account_data:
                account_data["code"] = f"{account_data['code']:<0{code_digits}}"

        for model in ("account.fiscal.position", "account.reconcile.model"):
            if model in data:
                data[model] = data.pop(model)
        _debug.pipeline(
            "pre_load_normalized",
            chart=template_code,
            company=company,
            fiscal_country=fiscal_country,
            code_digits=code_digits,
            models=len(data),
        )

        _debug.logic(
            "unknown_fields_drop",
            skipped=bool(self.env.context.get("l10n_check_fields_complete")),
        )
        if not self.env.context.get("l10n_check_fields_complete"):
            self._pre_load_drop_unknown_fields(data)
        self._pre_load_translate_untranslatable(template_code, company, data)
        return data

    @_debug.perf.timed
    def _load_deref_x2many(self, field, value):
        for i, (command, _id, *last_part) in enumerate(value):
            if last_part:
                last_part = last_part[0]
            if command in (Command.CREATE, Command.UPDATE):
                self._load_deref_values(last_part, self.env[field.comodel_name])
            elif command == Command.SET:
                for subvalue_idx, subvalue in enumerate(last_part):
                    if isinstance(subvalue, str):
                        last_part[subvalue_idx] = self.ref(subvalue).id
            elif command == Command.LINK and isinstance(_id, str):
                value[i] = Command.link(self.ref(_id).id)

    @_debug.perf.timed
    def _load_deref_many2one(self, values, fname, value, field, model, failed_fields):
        try:
            values[fname] = (
                self.ref(value).id if value not in ("", "False", "None") else False
            )
        except ValueError:
            _debug.logic(
                "many2one_ref_unresolved",
                field=fname,
                ref=value,
                company_fallback=model._name in ("res.company", "account.config"),
            )
            if model._name in ("res.company", "account.config"):
                current = self.env.company
                if model._name == "account.config":
                    current = current.account_config_id
                    root = self.env.company.root_id.account_config_id
                else:
                    root = self.env.company.root_id
                values[fname] = current[fname] or root[fname] or False
            else:
                _logger.warning(
                    "Failed when trying to recover %s for field=%s", value, field
                )
                failed_fields.append(fname)
                values[fname] = False

    @_debug.perf.timed
    def _load_deref_values(self, values, model):
        failed_fields = []
        for fname, value in list(values.items()):
            field = model._fields.get(fname)
            if field is None:
                continue
            if not value:
                values[fname] = False
            elif isinstance(value, str) and (
                field.type == "many2one"
                or (
                    field.type in ("integer", "many2one_reference")
                    and not value.isdigit()
                )
            ):
                self._load_deref_many2one(
                    values, fname, value, field, model, failed_fields
                )
            elif field.type in ("one2many", "many2many"):
                if isinstance(value[0], (list, tuple)):
                    self._load_deref_x2many(field, value)
                elif isinstance(value, str):
                    values[fname] = [
                        Command.set([self.ref(v).id for v in value.split(",") if v])
                    ]
        if _debug.logic.enabled and failed_fields:
            _debug.logic("deref_fields_dropped", model=model, fields=failed_fields)
        for fname in failed_fields:
            del values[fname]
        return values

    @_debug.perf.timed
    def _load_should_delay(
        self,
        created_models,
        yet_to_be_created_models,
        model,
        field_name,
        field_val,
        parent_models=None,
    ):
        parent_models = (parent_models or []) + [model]
        field = self.env[model]._fields.get(field_name)
        if (
            not field
            or not field.relational
            or field.comodel_name in created_models
            or isinstance(field_val, int)
        ):
            return False
        field_yet_to_be_created = (
            field.comodel_name in parent_models + yet_to_be_created_models
        )
        if not isinstance(field_val, list | tuple):
            return field_yet_to_be_created
        for element in field_val:
            match element:
                case Command.CREATE, _, dict() as values:
                    if any(
                        self._load_should_delay(
                            created_models,
                            yet_to_be_created_models,
                            field.comodel_name,
                            subkey,
                            subvalue,
                            parent_models,
                        )
                        for subkey, subvalue in values.items()
                    ):
                        return True
                case int() as command, *_ if command in tuple(Command):
                    if field_yet_to_be_created:
                        return True
        return False

    @_debug.perf.timed
    def _load_clears_default_repartition(self, model, field_name, xml_id, field_val):
        return (
            model == "account.tax"
            and field_name in REPARTITION_LINE_FIELDS
            and not self.ref(xml_id, raise_if_not_found=False)
            and all(
                isinstance(x, tuple | list)
                and len(x)
                and isinstance(x[0], Command | int)
                for x in field_val
            )
        )

    def _load_in_dependency_order(self, all_data):
        pending = deque(all_data)
        created_models = set()
        while pending:
            model, data = pending.popleft()
            yet_to_be_created_models = [model for model, _data in pending if _data]
            to_delay = defaultdict(dict)
            for xml_id, vals in data.items():
                to_be_removed = []
                for field_name, field_val in vals.items():
                    if not self._load_should_delay(
                        created_models,
                        yet_to_be_created_models,
                        model,
                        field_name,
                        field_val,
                    ):
                        continue
                    if self._load_clears_default_repartition(
                        model, field_name, xml_id, field_val
                    ):
                        field_val = [Command.clear()] + field_val
                    to_be_removed.append(field_name)
                    to_delay[xml_id][field_name] = field_val
                for field_name in to_be_removed:
                    del vals[field_name]
            _debug.pipeline(
                "model_load_ordered",
                model=model,
                records=len(data),
                delayed=len(to_delay),
                pending=len(pending),
            )
            if any(to_delay.values()):
                pending.append((model, to_delay))
            yield model, data
            created_models.add(model)

    @_debug.perf.timed
    def _load_record_vals(self, model, xml_id, record_vals):
        for key in list(record_vals):
            if "@" in key or key == "__translation_module__":
                del record_vals[key]
        if isinstance(xml_id, str) and (
            record := self.ref(xml_id, raise_if_not_found=False)
        ):
            xml_id = record.id
        if isinstance(xml_id, int):
            record_vals["id"] = xml_id
            xml_id = False
        else:
            xml_id = self.company_xmlid(xml_id)
        return {
            "xml_id": xml_id,
            "values": self._load_deref_values(record_vals, self.env[model]),
            "noupdate": True,
        }

    @_debug.perf.timed
    def _load_data(self, data):
        _debug.lifecycle("_load_data", records=self)
        created_records = {}
        for company_id in list(data.get("res.company", {})):
            self._split_company_config_data(
                self.env["res.company"].browse(company_id), data
            )
        for model, model_data in self._load_in_dependency_order(
            list(deepcopy(data).items())
        ):
            all_records_vals = [
                self._load_record_vals(model, xml_id, record_vals)
                for xml_id, record_vals in model_data.items()
            ]
            with _debug.perf(
                "_load_data",
                cr=self.env.cr,
                model=model,
                all_records_vals_count=len(all_records_vals),
            ):
                created_records[model] = (
                    self.with_context(lang="en_US")
                    .env[model]
                    ._load_records(all_records_vals)
                )
        return created_records

    @_debug.perf.timed
    def _post_load_journal_accounts(self, company):
        _debug.lifecycle("_post_load_journal_accounts", records=self)
        for journal in self.env["account.journal"].search(
            [
                ("type", "in", ["cash", "bank", "credit"]),
                ("company_id", "=", company.id),
            ]
        ):
            journal.suspense_account_id = (
                journal.suspense_account_id
                or company.account_config_id.account_journal_suspense_account_id
            )
            journal.profit_account_id = (
                journal.profit_account_id
                or company.account_config_id.default_cash_difference_income_account_id
            )
            journal.loss_account_id = (
                journal.loss_account_id
                or company.account_config_id.default_cash_difference_expense_account_id
            )
            if _debug.logic.enabled:
                _debug.logic(
                    "liquidity_journal_accounts",
                    company=company,
                    journal=journal,
                    suspense=journal.suspense_account_id,
                    profit=journal.profit_account_id,
                    loss=journal.loss_account_id,
                )

        if not company.account_config_id.tax_cash_basis_journal_id:
            company.account_config_id.tax_cash_basis_journal_id = self.ref(
                "caba", raise_if_not_found=False
            )
        if not company.account_config_id.currency_exchange_journal_id:
            company.account_config_id.currency_exchange_journal_id = self.ref(
                "exch", raise_if_not_found=False
            )

        sale_journal = self.ref("sale", raise_if_not_found=False)
        if sale_journal and company.account_config_id.income_account_id:
            sale_journal.default_account_id = (
                company.account_config_id.income_account_id
            )
        purchase_journal = self.ref("purchase", raise_if_not_found=False)
        if purchase_journal and company.account_config_id.expense_account_id:
            purchase_journal.default_account_id = (
                company.account_config_id.expense_account_id
            )
        if _debug.logic.enabled:
            _debug.logic(
                "company_journals_defaulted",
                company=company,
                caba_journal=company.account_config_id.tax_cash_basis_journal_id,
                exch_journal=company.account_config_id.currency_exchange_journal_id,
                sale_journal=sale_journal,
                sale_account=company.account_config_id.income_account_id,
                purchase_journal=purchase_journal,
                purchase_account=company.account_config_id.expense_account_id,
            )

    def _default_tax_for(self, company, type_tax_use):
        return (
            self.env["account.tax"]
            .search(
                [
                    *self.env["account.tax"]._check_company_domain(company),
                    ("type_tax_use", "in", type_tax_use),
                ],
                limit=1,
            )
            .id
        )

    def _force_company_default_tax_on_products(self, company, fname, tax_field):
        company_domain = self.env["product.template"]._check_company_domain(company)
        tax_domain = self.env["account.tax"]._check_company_domain(company)
        products = (
            self.env["product.template"]
            .sudo()
            .search(
                Domain.AND(
                    [
                        company_domain,
                        Domain(tax_field, "!=", False),
                        Domain(tax_field, "not any", tax_domain),
                    ]
                )
            )
        )
        products._force_default_tax_field(company, fname, tax_field)

    @_debug.perf.timed
    def _post_load_default_taxes(self, company):
        _debug.lifecycle("_post_load_default_taxes", records=self)
        if not company.account_config_id.account_sale_tax_id:
            company.account_config_id.account_sale_tax_id = self._default_tax_for(
                company, ("sale", "all")
            )
        if not company.account_config_id.account_purchase_tax_id:
            company.account_config_id.account_purchase_tax_id = self._default_tax_for(
                company, ("purchase", "all")
            )

        if company.account_config_id.account_sale_tax_id:
            self._force_company_default_tax_on_products(
                company, "account_sale_tax_id", "taxes_id"
            )
        if company.account_config_id.account_purchase_tax_id:
            self._force_company_default_tax_on_products(
                company, "account_purchase_tax_id", "supplier_taxes_id"
            )

        if not company.parent_id and self.env["account.tax"].search_count(
            [
                *self.env["account.tax"]._check_company_domain(company),
                ("tax_exigibility", "=", "on_payment"),
            ],
            limit=1,
        ):
            company.account_config_id.tax_exigibility = True
        if _debug.logic.enabled:
            _debug.logic(
                "default_taxes_resolved",
                company=company,
                sale_tax=company.account_config_id.account_sale_tax_id,
                purchase_tax=company.account_config_id.account_purchase_tax_id,
                tax_exigibility=company.account_config_id.tax_exigibility,
            )

    @_debug.perf.timed
    def _post_load_defaults(self, company, template_data):
        _debug.lifecycle("_post_load_defaults", records=self)
        for field, model in self._get_property_accounts().items():
            value = template_data.get(field)
            if not value or field not in self.env[model]._fields:
                continue
            _debug.logic(
                "property_default_set",
                company=company,
                field=field,
                model=model,
                ref=value,
            )
            if model == "res.company":
                owner = (
                    company if field in company._fields else company.account_config_id
                )
                owner[field] = self.ref(value)
            else:
                self.env["ir.default"].set(
                    model, field, self.ref(value).id, company_id=company.id
                )
        for field, account in (
            (
                "property_account_income_categ_id",
                company.account_config_id.income_account_id,
            ),
            (
                "property_account_expense_categ_id",
                company.account_config_id.expense_account_id,
            ),
        ):
            self.env["ir.default"].set(
                "product.category", field, account.id, company_id=company.id
            )

    @_debug.perf.timed
    def _post_load_reconcile_models(self, company):
        _debug.lifecycle("_post_load_reconcile_models", records=self)
        reco = self.ref("internal_transfer_reco", raise_if_not_found=False)
        if reco:
            reco.line_ids.sudo().write(
                {"account_id": company.account_config_id.transfer_account_id.id}
            )
        bank_fees = self.ref("bank_fees_reco", raise_if_not_found=False)
        if bank_fees:
            bank_fees.line_ids.sudo().write(
                {"account_id": self._get_bank_fees_reco_account(company).id}
            )

    @_debug.perf.timed
    def _post_load_data(self, template_code, company, template_data):
        _debug.lifecycle("_post_load_data", records=self)
        company = company or self.env.company

        self._setup_utility_bank_accounts(template_code, company, template_data)
        company.get_unaffected_earnings_account()
        self._post_load_journal_accounts(company)
        self._post_load_default_taxes(company)
        self._post_load_defaults(company, template_data)
        self._post_load_reconcile_models(company)
        company._initiate_account_onboardings()

    def _get_bank_fees_reco_account(self, company):
        AccountAccount = self.env["account.account"].with_company(company)
        domain = [*self.env["account.account"]._check_company_domain(company.id)]
        return AccountAccount.search(
            [*domain, ("name", "like", "Bank Fees")], limit=1
        ) or AccountAccount.search([*domain, ("account_type", "=", "expense")], limit=1)

    def _get_property_accounts(self):
        return {
            "property_account_receivable_id": "res.partner",
            "property_account_payable_id": "res.partner",
            "property_stock_journal": "product.category",
        }

    def _prepare_chart_template_model_data(self, template_code, model):
        data = defaultdict(dict)
        for code in [None] + self._get_parent_template(template_code):
            for func in self._template_register[code].get(model, []):
                values_by_xmlid = func(self, template_code)
                if values_by_xmlid is None:
                    continue
                for xmlid, values in values_by_xmlid.items():
                    data[xmlid].update(values)
        return dict(data)

    @_debug.perf.timed
    def _prepare_chart_template_data(self, template_code):
        template_data = defaultdict(lambda: defaultdict(dict))
        template_data["res.company"]
        translatable_model_fields = self._get_fields_translatable_template_model()
        untranslatable_model_fields = self._get_untranslatable_fields_to_translate()
        for code in [None] + self._get_parent_template(template_code):
            _debug.logic("template_level_applied", chart=template_code, level=code)
            for model, funcs in sorted(
                self._template_register[code].items(),
                key=lambda i: (
                    TEMPLATE_MODELS.index(i[0]) if i[0] in TEMPLATE_MODELS else 1000
                ),
            ):
                translatable_fields = translatable_model_fields.get(model, [])
                untranslatable_fields = untranslatable_model_fields.get(model, [])
                for func in funcs:
                    data = func(self, template_code)
                    if data is not None:
                        if model == "template_data":
                            template_data[model].update(data)
                        else:
                            for xmlid, record in data.items():
                                for field in (
                                    translatable_fields + untranslatable_fields
                                ):
                                    if field in record:
                                        record.setdefault("__translation_module__", {})[
                                            field
                                        ] = func._module

                                template_data[model][xmlid].update(record)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "template_data_collected",
                chart=template_code,
                records={
                    model: len(recs)
                    for model, recs in template_data.items()
                    if model != "template_data"
                },
                template_keys=len(template_data.get("template_data", {})),
            )
        return template_data

    @_debug.perf.timed
    def _prepare_utility_account_vals(
        self, company, template_data, bank_prefix="", code_digits=0
    ):
        bank_prefix = bank_prefix or company.account_config_id.bank_account_code_prefix
        code_digits = code_digits or int(template_data.get("code_digits", 6))
        _debug.logic(
            "utility_account_codes",
            company=company,
            bank_prefix=bank_prefix,
            code_digits=code_digits,
        )
        return {
            "account_journal_suspense_account_id": {
                "name": _("Bank Suspense Account"),
                "prefix": bank_prefix,
                "code_digits": code_digits,
                "account_type": "asset_current",
            },
            "account_journal_early_pay_discount_loss_account_id": {
                "name": _("Cash Discount Loss"),
                "code": str(10**code_digits - 2),
                "account_type": "expense",
            },
            "account_journal_early_pay_discount_gain_account_id": {
                "name": _("Cash Discount Gain"),
                "code": str(10**code_digits - 3),
                "account_type": "income_other",
            },
            "default_cash_difference_income_account_id": {
                "name": _("Cash Difference Gain"),
                "prefix": "999",
                "code_digits": code_digits,
                "account_type": "income_other",
                "tag_ids": [Command.set(self.ref("account.account_tag_investing").ids)],
            },
            "default_cash_difference_expense_account_id": {
                "name": _("Cash Difference Loss"),
                "prefix": "999",
                "code_digits": code_digits,
                "account_type": "expense",
                "tag_ids": [Command.set(self.ref("account.account_tag_investing").ids)],
            },
            "transfer_account_id": {
                "name": _("Liquidity Transfer"),
                "prefix": company.account_config_id.transfer_account_code_prefix,
                "code_digits": code_digits,
                "account_type": "asset_current",
                "reconcile": True,
            },
        }

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        bank_prefix = company.account_config_id.bank_account_code_prefix
        code_digits = int(template_data.get("code_digits", 6))
        accounts_data = self._prepare_utility_account_vals(company, template_data)
        config = company.account_config_id
        for fname in list(accounts_data):
            if config[fname]:
                del accounts_data[fname]
        _debug.logic(
            "utility_accounts_source",
            chart=template_code,
            company=company,
            missing=len(accounts_data),
            from_root=bool(company.parent_id),
        )
        if company.parent_id:
            for company_attr_name in accounts_data:
                config[company_attr_name] = company.root_id.account_config_id[
                    company_attr_name
                ]
        else:
            accounts = self.env["account.account"]._load_records(
                [
                    {
                        "xml_id": self.company_xmlid(xml_id, company),
                        "values": values,
                        "noupdate": True,
                    }
                    for xml_id, values in accounts_data.items()
                ]
            )
            for company_attr_name, account in zip(accounts_data, accounts, strict=True):
                config[company_attr_name] = account

            self._create_outstanding_accounts(company, bank_prefix, code_digits)

    @_debug.perf.timed
    def _create_outstanding_accounts(self, company, bank_prefix, code_digits):
        accounts_by_xmlid = {
            "account_journal_payment_debit_account_id": {
                "name": _("Outstanding Receipts"),
                "prefix": bank_prefix,
                "code_digits": code_digits,
                "account_type": "asset_current",
                "reconcile": True,
            },
            "account_journal_payment_credit_account_id": {
                "name": _("Outstanding Payments"),
                "prefix": bank_prefix,
                "code_digits": code_digits,
                "account_type": "asset_current",
                "reconcile": True,
            },
        }
        self.env["account.account"]._load_records(
            [
                {
                    "xml_id": self.company_xmlid(xml_id, company),
                    "values": values,
                    "noupdate": True,
                }
                for xml_id, values in accounts_by_xmlid.items()
            ]
        )

    @api.model
    def _foreign_tax_create_account(
        self, company, existing_account, additional_label, reconcilable=False
    ):
        new_code = (
            self.env["account.account"]
            .with_company(company)
            ._search_new_account_code(existing_account.code)
        )
        return self.env["account.account"].create(
            {
                "name": f"{existing_account.name} - {additional_label}",
                "code": new_code,
                "account_type": existing_account.account_type,
                "reconcile": reconcilable or existing_account.reconcile,
                "non_trade": existing_account.non_trade,
                "company_ids": [Command.link(company.id)],
            }
        )

    def _foreign_tax_group_account_fields(self, country):
        return (
            (
                "tax_payable_account_id",
                _("Foreign tax account payable (%s)", country.code),
            ),
            (
                "tax_receivable_account_id",
                _("Foreign tax account receivable (%s)", country.code),
            ),
            (
                "advance_tax_payment_account_id",
                _("Foreign tax account advance payment (%s)", country.code),
            ),
        )

    def _foreign_tax_map_group_accounts(
        self, company, country, tax_group_data, existing_accounts
    ):
        account_fields = list(self._foreign_tax_group_account_fields(country))
        local_tax_group_per_field = {
            field: self.env["account.tax.group"].search(
                [
                    *self.env["account.tax.group"]._check_company_domain(company),
                    (
                        "country_id",
                        "=",
                        company.account_config_id.account_fiscal_country_id.id,
                    ),
                    (field, "!=", False),
                ],
                limit=1,
            )
            for field, _account_name in account_fields
        }
        accounts_before = len(existing_accounts)  # debuglog
        for field, account_name in account_fields:
            for tax_group in tax_group_data.values():
                account_template_xml_id = tax_group.get(field)
                if account_template_xml_id in existing_accounts:
                    continue
                local_tax_group = local_tax_group_per_field[field]
                if local_tax_group:
                    existing_accounts[account_template_xml_id] = (
                        self._foreign_tax_create_account(
                            company, local_tax_group[field], account_name
                        ).id
                    )
        if _debug.logic.enabled:
            _debug.logic(
                "foreign_group_accounts_mapped",
                company=company,
                country=country,
                created=len(existing_accounts) - accounts_before,
                local_group_fields=[
                    f for f, g in local_tax_group_per_field.items() if g
                ],
            )

    def _foreign_tax_find_similar_repartition_line(
        self, company, type_tax_use, rep_line, default_company_taxes
    ):
        sign_comparator = "<" if float(rep_line.get("factor_percent", 100)) < 0 else ">"
        minimal_domain = [
            *self.env["account.tax.repartition.line"]._check_company_domain(company),
            ("account_id", "!=", False),
            ("factor_percent", sign_comparator, 0),
        ]
        additional_domain = [
            ("tax_id.type_tax_use", "=", type_tax_use),
            (
                "tax_id.country_id",
                "=",
                company.account_config_id.account_fiscal_country_id.id,
            ),
            ("tax_id", "in", default_company_taxes.ids),
        ]
        while additional_domain:
            found = self.env["account.tax.repartition.line"].search(
                minimal_domain + additional_domain, limit=1
            )
            if found:
                return found
            additional_domain.pop()
        return self.env["account.tax.repartition.line"]

    def _foreign_tax_map_repartition_accounts(
        self, company, country, tax_data, existing_accounts, default_company_taxes
    ):
        accounts_before = len(existing_accounts)  # debuglog
        for tax_template in tax_data.values():
            for _command, _id, rep_line in tax_template.get("repartition_line_ids", []):
                if (
                    "account_id" not in rep_line
                    or rep_line["repartition_type"] != "tax"
                ):
                    continue
                account_template_xml_id = rep_line["account_id"]
                if account_template_xml_id in existing_accounts:
                    continue
                similar = self._foreign_tax_find_similar_repartition_line(
                    company,
                    tax_template["type_tax_use"],
                    rep_line,
                    default_company_taxes,
                )
                if similar:
                    existing_accounts[account_template_xml_id] = (
                        self._foreign_tax_create_account(
                            company,
                            similar.account_id,
                            _("Foreign tax account (%s)", country.code),
                        ).id
                    )
        _debug.logic(
            "foreign_repartition_accounts_mapped",
            company=company,
            country=country,
            taxes=len(tax_data),
            created=len(existing_accounts) - accounts_before,
        )

    @_debug.perf.timed
    def _foreign_tax_map_cash_basis_accounts(
        self, company, tax_data, existing_accounts
    ):
        local_cash_basis_tax = self.env["account.tax"].search(
            [
                *self.env["account.tax"]._check_company_domain(company),
                (
                    "country_id",
                    "=",
                    company.account_config_id.account_fiscal_country_id.id,
                ),
                ("tax_exigibility", "=", "on_payment"),
                ("cash_basis_transition_account_id", "!=", False),
            ],
            limit=1,
        )
        _debug.logic(
            "local_cash_basis_tax",
            company=company,
            tax=local_cash_basis_tax,
            tax_templates=len(tax_data),
        )
        has_cash_basis = False
        for tax_template in sorted(
            tax_data.values(),
            key=lambda x: any(
                rep_line.get("account_id")
                for _command, _id, rep_line in x.get("repartition_line_ids", [])
            ),
            reverse=True,
        ):
            if tax_template.get("tax_exigibility") != "on_payment":
                continue
            has_cash_basis = True
            account_xml_id = tax_template.get("cash_basis_transition_account_id")
            if account_xml_id in existing_accounts:
                continue
            label = _("Cash basis transition account")
            if local_cash_basis_tax:
                _debug.logic("cash_basis_from_local_tax", account_xmlid=account_xml_id)
                existing_accounts[account_xml_id] = self._foreign_tax_create_account(
                    company,
                    local_cash_basis_tax.cash_basis_transition_account_id,
                    label,
                    reconcilable=True,
                ).id
            elif account_ids := [
                rep_line["account_id"]
                for _command, _id, rep_line in tax_template.get(
                    "repartition_line_ids", []
                )
                if rep_line.get("account_id")
            ]:
                _debug.logic(
                    "cash_basis_from_repartition",
                    account_xmlid=account_xml_id,
                    repartition_account_xmlid=account_ids[0],
                )
                local_account = self.env["account.account"].browse(
                    existing_accounts.get(account_ids[0])
                )
                existing_accounts[account_xml_id] = self._foreign_tax_create_account(
                    company, local_account, label, reconcilable=True
                ).id
            else:
                _debug.logic(
                    "cash_basis_account_unresolved", account_xmlid=account_xml_id
                )
                existing_accounts[account_xml_id] = None
        _debug.logic(
            "cash_basis_mapped", company=company, has_cash_basis=has_cash_basis
        )
        return has_cash_basis

    def _foreign_tax_apply_account_map(
        self, country, chart_template_code, tax_group_data, tax_data, existing_accounts
    ):
        for field, _account_name in self._foreign_tax_group_account_fields(country):
            for tax_group in tax_group_data.values():
                tax_group[field] = existing_accounts.get(tax_group.get(field))

        for tax_template in tax_data.values():
            tax_template["country_id"] = country.id
            if tax_template.get("tax_group_id"):
                tax_template["tax_group_id"] = (
                    f"{chart_template_code}_{tax_template['tax_group_id']}"
                )
            for _command, _id, rep_line in tax_template.get("repartition_line_ids", []):
                rep_line["account_id"] = existing_accounts.get(
                    rep_line.get("account_id")
                )
            tax_template.pop("fiscal_position_ids", None)
            tax_template.pop("original_tax_ids", None)
            if account_xml_id := tax_template.get("cash_basis_transition_account_id"):
                tax_template["cash_basis_transition_account_id"] = (
                    existing_accounts.get(account_xml_id)
                )
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "foreign_tax_accounts_applied",
                country=country,
                chart=chart_template_code,
                tax_groups=len(tax_group_data),
                taxes=len(tax_data),
                accounts=len(existing_accounts),
                unresolved=sum(1 for v in existing_accounts.values() if not v),
            )

    def _foreign_tax_prefix_xmlids(self, chart_template_code, data):
        prefixed = {
            model: {
                f"{chart_template_code}_{xml_id}": template
                for xml_id, template in templates.items()
            }
            for model, templates in data.items()
        }
        for tax_values in prefixed["account.tax"].values():
            if tax_values.get("amount_type") == "group" and (
                children := tax_values.get("children_tax_ids")
            ):
                tax_values["children_tax_ids"] = ",".join(
                    f"{chart_template_code}_{child}" for child in children.split(",")
                )
        return prefixed

    @api.model
    @_debug.perf.timed
    def _instantiate_foreign_taxes(self, country, company):
        taxes_in_country = self.env["account.tax"].search(
            [
                *self.env["account.tax"]._check_company_domain(company),
                ("country_id", "=", country.id),
            ]
        )
        if taxes_in_country:
            _debug.logic(
                "foreign_taxes_exist",
                company=company,
                country=country,
                taxes=len(taxes_in_country),
            )
            return {"account.tax": taxes_in_country}

        existing_accounts = {"": None, None: None}
        default_company_taxes = (
            company.account_config_id.account_sale_tax_id
            + company.account_config_id.account_purchase_tax_id
        )
        chart_template_code = self._guess_chart_template(country=country)
        chart_template_data = self._prepare_chart_template_data(chart_template_code)
        tax_group_data = chart_template_data["account.tax.group"]
        tax_data = chart_template_data["account.tax"]
        _debug.pipeline(
            "foreign_chart_guessed",
            chart=chart_template_code,
            company=company,
            country=country,
            tax_groups=len(tax_group_data),
            taxes=len(tax_data),
            default_taxes=default_company_taxes,
        )

        self._foreign_tax_map_group_accounts(
            company, country, tax_group_data, existing_accounts
        )
        self._foreign_tax_map_repartition_accounts(
            company, country, tax_data, existing_accounts, default_company_taxes
        )
        if self._foreign_tax_map_cash_basis_accounts(
            company, tax_data, existing_accounts
        ):
            company.account_config_id.tax_exigibility = True

        self._foreign_tax_apply_account_map(
            country, chart_template_code, tax_group_data, tax_data, existing_accounts
        )
        _debug.pipeline(
            "foreign_accounts_mapped",
            chart=chart_template_code,
            company=company,
            accounts=len(existing_accounts) - 2,
        )
        return self._load_data(
            self._foreign_tax_prefix_xmlids(
                chart_template_code,
                {"account.tax.group": tax_group_data, "account.tax": tax_data},
            )
        )

    @template(model="account.account")
    def _get_account_account(self, template_code):
        return self._prepare_csv_vals(template_code, "account.account")

    @template(model="account.group")
    def _get_account_group(self, template_code):
        return self._prepare_csv_vals(template_code, "account.group")

    @template(model="account.tax.group")
    def _get_account_tax_group(self, template_code):
        return self._prepare_csv_vals(template_code, "account.tax.group")

    @template(model="account.tax")
    def _get_account_tax(self, template_code):
        tax_data = self._prepare_csv_vals(template_code, "account.tax")
        self._deref_account_tags(template_code, tax_data)
        return tax_data

    @template(model="account.fiscal.position")
    def _get_account_fiscal_position(self, template_code):
        return self._prepare_csv_vals(template_code, "account.fiscal.position")

    @template(model="account.journal")
    @_debug.perf.timed
    def _get_account_journal(self, template_code):
        return {
            "sale": {
                "name": _("Sales"),
                "type": "sale",
                "code": _("INV"),
                "show_on_dashboard": True,
                "color": 11,
                "sequence": 5,
            },
            "purchase": {
                "name": _("Purchases"),
                "type": "purchase",
                "code": _("BILL"),
                "show_on_dashboard": True,
                "color": 11,
                "sequence": 6,
            },
            "general": {
                "name": _("Miscellaneous Operations"),
                "type": "general",
                "code": _("MISC"),
                "show_on_dashboard": False,
                "sequence": 9,
            },
            "exch": {
                "name": _("Exchange Difference"),
                "type": "general",
                "code": _("EXCH"),
                "show_on_dashboard": False,
            },
            "caba": {
                "name": _("Cash Basis Taxes"),
                "type": "general",
                "code": _("CABA"),
                "show_on_dashboard": False,
            },
            "bank": {
                "name": _("Bank"),
                "type": "bank",
                "show_on_dashboard": True,
                "sequence": 7,
            },
        }

    @template(model="account.reconcile.model")
    def _get_account_reconcile_model(self, template_code):
        return {
            "internal_transfer_reco": {
                "name": _("Internal Transfers"),
                "line_ids": [
                    Command.create(
                        {
                            "amount_type": "percentage",
                            "amount_string": "100",
                            "label": _("Internal Transfers"),
                        }
                    ),
                ],
            },
            "bank_fees_reco": {
                "name": _("Bank Fees"),
                "match_label": "contains",
                "match_label_param": "Bank Fees",
                "line_ids": [
                    Command.create(
                        {
                            "label": _("Bank Fees"),
                            "amount_type": "percentage",
                            "amount_string": "100",
                        }
                    ),
                ],
            },
        }

    def company_xmlid(self, xmlid, company=None):
        if "." in xmlid:
            return xmlid
        company = company or self.env.company
        return f"account.{company.id}_{xmlid}"

    def ref(self, xmlid, raise_if_not_found=True):
        company_xmlid = self.company_xmlid(xmlid)
        if "." in xmlid:
            return self.env.ref(company_xmlid, raise_if_not_found)
        return self.env.ref(company_xmlid, raise_if_not_found=False) or self.env.ref(
            self.company_xmlid(xmlid, self.env.company.root_id), raise_if_not_found
        )

    def _get_parent_template(self, code):
        parents = []
        template_mapping = self._get_chart_template_mapping(get_all=True)
        while template_mapping.get(code):
            parents.append(code)
            code = template_mapping.get(code).get("parent")
        return parents

    @_debug.perf.timed
    def _get_tag_mapper(self, country_id):
        tags = {
            x.name: x.id
            for x in self.env["account.account.tag"]
            .with_context(active_test=False, lang="en_US")
            .search(
                [
                    ("applicability", "=", "taxes"),
                    ("country_id", "=", country_id),
                ]
            )
        }
        _debug.pipeline(
            "tax_tags_indexed",
            country=country_id,
            tags=len(tags),
            ignore_missing=self.env.context.get("ignore_missing_tags"),
        )

        def mapping_getter(*args):
            res = []
            for tag in args:
                if (match := re.match(r"^(?P<module>\w+)\.\w+$", tag)) and self.env[
                    "ir.module.module"
                ]._get(match.group("module")):
                    res.append(tag)
                else:
                    format_tag = re.sub(r"\s+", " ", tag.strip())
                    mapped_tag = tags.get(format_tag)
                    if not mapped_tag:
                        country = self.env["res.country"].browse(country_id)
                        if not self.env.context.get("ignore_missing_tags"):
                            _debug.logic(
                                "missing_tax_tag_raised",
                                country=country_id,
                                tag=format_tag,
                            )
                            raise RedirectWarning(
                                message=self.env._(
                                    "Error while loading the localization: missing tax tag %(tag_name)s for country %(country_name)s."
                                    " You should probably update your localization app first.",
                                    tag_name=format_tag,
                                    country_name=country.name,
                                ),
                                action={
                                    "name": self.env._("Need to update"),
                                    "res_model": "ir.module.module",
                                    "type": "ir.actions.act_window",
                                    "views": [
                                        (
                                            self.env.ref("base.module_view_kanban").id,
                                            "kanban",
                                        )
                                    ],
                                    "context": {
                                        "search_default_name": country.name,
                                        "search_default_category_id": self.env.ref(
                                            "base.module_category_accounting_localizations_account_charts"
                                        ).id,
                                    },
                                },
                                button_text=self.env._("Update app"),
                            )
                        _logger.error(
                            "Error while loading the localization: missing tax tag %s for country %s."
                            " You should probably update your localization app first.",
                            format_tag,
                            country.name,
                        )
                        continue
                    res.append(mapped_tag)
            if _debug.logic.enabled and len(res) != len(args):
                _debug.logic(
                    "tax_tags_dropped",
                    country=country_id,
                    requested=len(args),
                    mapped=len(res),
                )
            return res

        return mapping_getter

    def _deref_account_tags(self, template_code, tax_data):
        mapper = self._get_tag_mapper(
            self._get_chart_template_mapping(get_all=True)[template_code]["country_id"]
        )
        for tax_values in tax_data.values():
            for field_name in REPARTITION_LINE_FIELDS:
                for element in tax_values.get(field_name, []):
                    match element:
                        case int() as command, _, {
                            "tag_ids": str() as tags
                        } as values if command in tuple(Command):
                            values["tag_ids"] = [
                                Command.set(mapper(*tags.split(TAX_TAG_DELIMITER)))
                            ]

    def _parse_csv_value(self, key, value, available_fields):
        if not value or "@" in key:
            return value
        field = available_fields.get(key)
        if field is None:
            return value
        if field.type in ("boolean", "integer", "float"):
            return ast.literal_eval(value)
        if field.type == "char":
            return value.strip()
        return value

    def _resolve_csv_comodel(self, Model, path):
        for path_component in path:
            field = Model._fields.get(path_component)
            if field is None or not field.relational:
                return None
            Model = self.env[field.comodel_name]
        return Model

    @_debug.perf.timed
    def _update_csv_vals_from_row(self, Model, res, row, last_id, filename, line_no):
        if row["id"]:
            last_id = row["id"]
            res[last_id].update(
                {
                    key: self._parse_csv_value(key, value, Model._fields)
                    for key, value in row.items()
                    if key != "id" and value and ("@" in key or key in Model._fields)
                }
            )
        create_added = set()
        for key, value in row.items():
            if "/" not in key or not value:
                continue
            if last_id is None:
                _debug.logic(
                    "csv_subrecord_orphaned", file=filename, line_no=line_no, column=key
                )
                raise ValueError(
                    f"{filename}, line {line_no}: column {key!r} belongs to a "
                    f"sub-record, but no row with an 'id' has been read yet for it "
                    f"to attach to."
                )
            *model_path, fname = key.split("/")
            SubModel = self._resolve_csv_comodel(Model, model_path)
            if SubModel is None or fname not in SubModel._fields:
                _logger.warning(
                    "%s, line %s: ignoring column %r, %r has no such field",
                    filename,
                    line_no,
                    key,
                    SubModel._name if SubModel else Model._name,
                )
                continue
            sub = res[last_id]
            prefix = ""
            for path_component in model_path:
                prefix = f"{prefix}/{path_component}" if prefix else path_component
                if prefix not in create_added:
                    create_added.add(prefix)
                    sub.setdefault(path_component, [])
                    sub[path_component].append(Command.create({}))
                sub = sub[path_component][-1][2]
            sub[fname] = self._parse_csv_value(fname, value, SubModel._fields)
        return last_id

    @_debug.perf.timed
    def _prepare_csv_vals(self, template_code, model, module=None):
        Model = self.env[model]
        if module is None:
            module = self._get_chart_template_mapping(get_all=True)[template_code][
                "module"
            ]
        assert re.fullmatch(r"[a-z0-9_]+", module)

        res = defaultdict(dict)
        for template in self._get_parent_template(template_code)[::-1] or [""]:
            suffix = f"-{template}" if template else ""
            filename = f"{module}/data/template/{model}{suffix}.csv"
            try:
                with file_open(filename, "r") as csv_file:
                    last_id = None
                    for line_no, row in enumerate(csv.DictReader(csv_file), start=2):
                        last_id = self._update_csv_vals_from_row(
                            Model, res, row, last_id, filename, line_no
                        )
            except FileNotFoundError:
                _debug.logic(
                    "csv_template_missing",
                    chart=template_code,
                    model=model,
                    file=filename,
                )
                _logger.debug("No file %s found for template '%s'", model, module)
        _debug.pipeline(
            "csv_vals_prepared", chart=template_code, model=model, records=len(res)
        )
        return dict(res)

    def _template_company_field(self, model):
        return (
            "company_id" if "company_id" in self.env[model]._fields else "company_ids"
        )

    def _get_untranslatable_fields_target_language(self, template_code, company):
        return company.partner_id.lang or get_lang(self.env).code

    def _get_untranslatable_fields_to_translate(self):
        return {
            "account.journal": [
                "code",
            ],
        }

    def _get_fields_translatable_template_model(self):
        return {
            model: [
                fieldname
                for (fieldname, field) in self.env[model]._fields.items()
                if field.translate
            ]
            for model in TEMPLATE_MODELS
        }

    @_debug.perf.timed
    def _get_untranslated_translatable_template_model_records(self, langs, companies):
        if not langs or not companies:
            _debug.logic(
                "untranslated_scan_skipped",
                reason="no_langs" if not langs else "no_companies",
            )
            return []

        company_ids = tuple(companies.ids)

        translatable_model_fields = self._get_fields_translatable_template_model()

        queries = []
        for model in TEMPLATE_MODELS:
            translatable_fields = translatable_model_fields[model]
            if not translatable_fields:
                continue
            company_id_field = self._template_company_field(model)

            self.env[model].flush_model(
                ["id", company_id_field] + translatable_model_fields[model]
            )

            query = self.env[model]._search(
                [(company_id_field, "in", company_ids)], bypass_access=True
            )

            missing_translation_clauses = [
                SQL("(%s ->> %s) IS NULL", SQL.identifier(query.table, field), lang)
                for field in translatable_fields
                for lang in langs
            ]

            translatable_field_column_args = []
            for field in translatable_fields:
                translatable_field_column_args.extend(
                    (SQL("%s::text", field), SQL.identifier(query.table, field))
                )

            queries.append(
                SQL(
                    """
                 SELECT %(model)s AS model,
                        model_data.name AS xmlid,
                        model_data.module AS module,
                        json_build_object(%(translatable_field_column_args)s) AS fields
                   FROM %(from_clause)s
                   JOIN ir_model_data model_data ON model_data.model = %(model)s
                                                AND %(model_id)s = model_data.res_id
                  WHERE %(where_clause)s
                        AND (%(missing_translation_clauses)s)
                """,
                    model=SQL("%s::text", model),
                    translatable_field_column_args=SQL(", ").join(
                        translatable_field_column_args
                    ),
                    from_clause=query.from_clause,
                    model_id=SQL.identifier(query.table, "id"),
                    where_clause=query.where_clause or SQL("TRUE"),
                    missing_translation_clauses=SQL(" OR ").join(
                        missing_translation_clauses
                    ),
                )
            )

        query = SQL(" UNION ALL ").join(queries)
        _debug.pipeline(
            "untranslated_query_built",
            companies=companies,
            langs=len(langs),
            models=len(queries),
        )
        self.env["ir.model.data"].flush_model(["res_id", "model", "name"])

        self.env.cr.execute(query)
        return self.env.cr.fetchall()

    def _get_field_translation(self, record, fname, lang):
        generic_lang = lang.split("_")[0]
        translation_module = record.get("__translation_module__", {}).get(
            fname, "account"
        )
        translation = record.get(f"{fname}@{lang}") or record.get(
            f"{fname}@{generic_lang}"
        )
        if translation or fname not in record:
            return translation
        else:
            return code_translations.get_python_translations(
                translation_module, lang
            ).get(record[fname]) or code_translations.get_python_translations(
                translation_module, generic_lang
            ).get(record[fname])

    @_debug.perf.timed
    def _collect_template_translations(
        self, translation_importer, langs, companies, template_data
    ):
        for company in companies:
            chart_template_data = template_data or self.env[
                "account.chart.template"
            ].with_context(ignore_missing_tags=True).with_company(
                company
            ).sudo()._prepare_chart_template_data(
                company.account_config_id.chart_template
            )
            if _debug.pipeline.enabled:
                _debug.pipeline(
                    "template_translations_collecting",
                    company=company,
                    chart=company.account_config_id.chart_template,
                    reused_template_data=bool(template_data),
                    langs=len(langs),
                    models=len(chart_template_data),
                )
            for mname, data in chart_template_data.items():
                if mname == "template_data":
                    continue
                for _xml_id, record in data.items():
                    fnames = {
                        fname.split("@")[0]
                        for fname in record
                        if fname != "__translation_module__"
                    }
                    for lang in langs:
                        for fname in fnames:
                            field = self.env[mname]._fields.get(fname)
                            if not field or not field.translate:
                                continue
                            field_translation = self._get_field_translation(
                                record, fname, lang
                            )
                            if field_translation:
                                xml_id = (
                                    _xml_id
                                    if "." in _xml_id
                                    else self.company_xmlid(_xml_id, company)
                                )
                                translation_importer.model_translations[mname][fname][
                                    xml_id
                                ][lang] = field_translation

    @_debug.perf.timed
    def _collect_code_translations(
        self, translation_importer, translation_langs, companies
    ):
        _debug.pipeline(
            "code_translations_collecting",
            companies=companies,
            langs=len(translation_langs),
        )
        for (
            mname,
            _xml_id,
            module,
            fields,
        ) in self._get_untranslated_translatable_template_model_records(
            translation_langs, companies
        ):
            for field, value in fields.items():
                if not value or "en_US" not in value:
                    continue
                value_en_US = value["en_US"]
                xml_id = f"{module}.{_xml_id}"
                for lang in [lang for lang in translation_langs if lang not in value]:
                    if (
                        lang
                        in translation_importer.model_translations[mname][field][xml_id]
                    ):
                        continue
                    value_translated = None
                    for code_module in (
                        [module, "account"] if module != "account" else ["account"]
                    ):
                        value_translated = get_python_translation(
                            code_module, lang, value_en_US
                        )
                        if not value_translated and (
                            re.match(r"<div>.*</div>", value_en_US)
                        ):
                            value_translated = get_python_translation(
                                code_module, lang, value_en_US[5:-6]
                            )
                            if value_translated:
                                value_translated = f"<div>{value_translated}</div>"
                        if value_translated:
                            translation_importer.model_translations[mname][field][
                                xml_id
                            ][lang] = value_translated
                            break

    @_debug.perf.timed
    def _load_translations(self, langs=None, companies=None, template_data=None):
        langs = langs or [code for code, _name in self.env["res.lang"].get_installed()]
        available_template_codes = list(self._get_chart_template_mapping(get_all=True))
        companies = companies or (
            self.env["account.config"]
            .search([("chart_template", "in", available_template_codes)])
            .company_id
        )

        translation_importer = TranslationImporter(self.env.cr, verbose=False)
        self._collect_template_translations(
            translation_importer, langs, companies, template_data
        )
        self._collect_code_translations(
            translation_importer,
            [lang for lang in langs if lang != "en_US"],
            companies,
        )
        translation_importer.save(overwrite=False)
