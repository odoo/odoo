# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        res = super(AccountChartTemplate, self)._load(company)
        # Copy chart of account translations when loading chart of account
        for chart_template in self.filtered('spoken_languages'):
            external_id = self.env['ir.model.data'].search([
                ('model', '=', 'account.chart.template'),
                ('res_id', '=', chart_template.id),
            ], order='id', limit=1)
            module = external_id and self.env.ref('base.module_' + external_id.module)
            if module and module.state == 'installed':
                langs = chart_template._get_langs()
                if langs:
                    chart_template._process_single_company_coa_translations(company.id, langs)
        return res

    def process_translations(self, langs, in_field, in_ids, out_ids):
        """
        This method copies translations values of templates into new Accounts/Taxes/Journals for languages selected

        :param langs: List of languages to load for new records
        :param in_field: Name of the translatable field of source templates
        :param in_ids: Recordset of ids of source object
        :param out_ids: Recordset of ids of destination object

        :return: True
        """
        for lang in langs:
            for in_id, out_id in zip(in_ids.with_context(lang=lang), out_ids.with_context(lang=lang)):
                out_id[in_field] = in_id[in_field]
        return True

    def process_coa_translations(self):
        company_obj = self.env['res.company']
        for chart_template_id in self:
            langs = chart_template_id._get_langs()
            if langs:
                company_ids = company_obj.search([('chart_template_id', '=', chart_template_id.id)])
                for company in company_ids:
                    chart_template_id._process_single_company_coa_translations(company.id, langs)
        return True

    def _process_single_company_coa_translations(self, company_id, langs):
        # write account.account translations in the real COA
        self._process_accounts_translations(company_id, langs, 'name')
        # write account.group translations
        self._process_account_group_translations(company_id, langs, 'name')
        # copy account.tax name translations
        self._process_taxes_translations(company_id, langs, 'name')
        # copy account.tax description translations
        self._process_taxes_translations(company_id, langs, 'description')
        # copy account.fiscal.position translations
        self._process_fiscal_pos_translations(company_id, langs, 'name')

    def _get_langs(self):
        if not self.spoken_languages:
            return []

        installed_langs = dict(self.env['res.lang'].get_installed())
        langs = []
        for lang in self.spoken_languages.split(';'):
            if lang not in installed_langs:
                # the language is not installed, so we don't need to load its translations
                continue
            else:
                langs.append(lang)
        return langs

    def _process_accounts_translations(self, company_id, langs, field):
        in_ids, out_ids = self._get_template_from_model(company_id, 'account.account')
        return self.process_translations(langs, field, in_ids, out_ids)

    def _process_account_group_translations(self, company_id, langs, field):
        in_ids, out_ids = self._get_template_from_model(company_id, 'account.group')
        return self.process_translations(langs, field, in_ids, out_ids)

    def _process_taxes_translations(self, company_id, langs, field):
        in_ids, out_ids = self._get_template_from_model(company_id, 'account.tax')
        return self.process_translations(langs, field, in_ids, out_ids)

    def _process_fiscal_pos_translations(self, company_id, langs, field):
        in_ids, out_ids = self._get_template_from_model(company_id, 'account.fiscal.position')
        return self.process_translations(langs, field, in_ids, out_ids)

    def _get_template_from_model(self, company_id, model):
        """ Find the records and their matching template """
        # generated records have an external id with the format <company id>_<template xml id>
        grouped_out_data = defaultdict(lambda: self.env['ir.model.data'])
        for imd in self.env['ir.model.data'].search([
                ('model', '=', model),
                ('name', '=like', str(company_id) + '_%')
            ]):
            grouped_out_data[imd.module] += imd

        in_records = self.env[model + '.template']
        out_records = self.env[model]
        for module, out_data in grouped_out_data.items():
            # templates and records may have been created in a different order
            # reorder them based on external id names
            expected_in_xml_id_names = {xml_id.name.partition(str(company_id) + '_')[-1]: xml_id for xml_id in out_data}

            in_xml_ids = self.env['ir.model.data'].search([
                ('model', '=', model + '.template'),
                ('module', '=', module),
                ('name', 'in', list(expected_in_xml_id_names))
            ])
            in_xml_ids = {xml_id.name: xml_id for xml_id in in_xml_ids}

            for name, xml_id in expected_in_xml_id_names.items():
                # ignore nonconforming customized data
                if name not in in_xml_ids:
                    continue
                in_records += self.env[model + '.template'].browse(in_xml_ids[name].res_id)
                out_records += self.env[model].browse(xml_id.res_id)

        return (in_records, out_records)

class BaseLanguageInstall(models.TransientModel):
    """ Install Language"""
    _inherit = "base.language.install"

    def lang_install(self):
        self.ensure_one()
        installed = {code for code, __ in self.env['res.lang'].get_installed()}
        res = super(BaseLanguageInstall, self).lang_install()
        to_install = set(self.lang_ids.mapped('code')) - installed
        if not to_install:
            # update of translations instead of new installation
            # skip to avoid duplicating the translations
            return res

        # CoA in multilang mode
        for coa in self.env['account.chart.template'].search([('spoken_languages', '!=', False)]):
            coa_langs_codes = to_install & set(coa.spoken_languages.split(';'))
            if coa_langs_codes:
                # companies on which it is installed
                for company in self.env['res.company'].search([('chart_template_id', '=', coa.id)]):
                    # write account.account translations in the real COA
                    coa.sudo()._process_accounts_translations(company.id, coa_langs_codes, 'name')
                    # write account.group translations
                    coa.sudo()._process_account_group_translations(company.id, coa_langs_codes, 'name')
                    # copy account.tax name translations
                    coa.sudo()._process_taxes_translations(company.id, coa_langs_codes, 'name')
                    # copy account.tax description translations
                    coa.sudo()._process_taxes_translations(company.id, coa_langs_codes, 'description')
                    # copy account.fiscal.position translations
                    coa.sudo()._process_fiscal_pos_translations(company.id, coa_langs_codes, 'name')

        return res
