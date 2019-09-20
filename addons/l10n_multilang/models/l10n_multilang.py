# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def load_for_current_company(self, sale_tax_rate, purchase_tax_rate):
        res = super(AccountChartTemplate, self).load_for_current_company(sale_tax_rate, purchase_tax_rate)
        # Copy chart of account translations when loading chart of account
        for chart_template in self.filtered('spoken_languages'):
            external_id = self.env['ir.model.data'].search([
                ('model', '=', 'account.chart.template'),
                ('res_id', '=', chart_template.id),
            ], order='id', limit=1)
            module = external_id and self.env.ref('base.module_' + external_id.module)
            if module and module.state == 'installed':
                chart_template.process_coa_translations()
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
        xlat_obj = self.env['ir.translation']
        #find the source from Account Template
        for lang in langs:
            #find the value from Translation
            value = xlat_obj._get_ids(in_ids._name + ',' + in_field, 'model', lang, in_ids.ids)
            counter = 0
            for element in in_ids.with_context(lang=None):
                if value[element.id]:
                    #copy Translation from Source to Destination object
                    xlat_obj._set_ids(
                        out_ids._name + ',' + in_field,
                        'model',
                        lang,
                        out_ids[counter].ids,
                        value[element.id],
                        element[in_field]
                    )
                else:
                    _logger.info('Language: %s. Translation from template: there is no translation available for %s!' % (lang, element[in_field]))
                counter += 1
        return True

    def process_coa_translations(self):
        installed_langs = dict(self.env['res.lang'].get_installed())
        company_obj = self.env['res.company']
        for chart_template_id in self:
            langs = []
            if chart_template_id.spoken_languages:
                for lang in chart_template_id.spoken_languages.split(';'):
                    if lang not in installed_langs:
                        # the language is not installed, so we don't need to load its translations
                        continue
                    else:
                        langs.append(lang)
                if langs:
                    company_ids = company_obj.search([('chart_template_id', '=', chart_template_id.id)])
                    for company in company_ids:
                        # write account.account translations in the real COA
                        chart_template_id._process_accounts_translations(company.id, langs, 'name')
                        # copy account.tax name translations
                        chart_template_id._process_taxes_translations(company.id, langs, 'name')
                        # copy account.tax description translations
                        chart_template_id._process_taxes_translations(company.id, langs, 'description')
                        # copy account.fiscal.position translations
                        chart_template_id._process_fiscal_pos_translations(company.id, langs, 'name')
        return True

    def _process_accounts_translations(self, company_id, langs, field):
        in_ids, out_ids = self._get_template_from_model(company_id, 'account.account')
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
        already_installed = self.lang in [code for code, _ in self.env['res.lang'].get_installed()]
        res = super(BaseLanguageInstall, self).lang_install()
        if already_installed:
            # update of translations instead of new installation
            # skip to avoid duplicating the translations
            return res

        # CoA in multilang mode
        for coa in self.env['account.chart.template'].search([('spoken_languages', '!=', False)]):
            if self.lang in coa.spoken_languages.split(';'):
                # companies on which it is installed
                for company in self.env['res.company'].search([('chart_template_id', '=', coa.id)]):
                    # write account.account translations in the real COA
                    coa._process_accounts_translations(company.id, [self.lang], 'name')
                    # copy account.tax name translations
                    coa._process_taxes_translations(company.id, [self.lang], 'name')
                    # copy account.tax description translations
                    coa._process_taxes_translations(company.id, [self.lang], 'description')
                    # copy account.fiscal.position translations
                    coa._process_fiscal_pos_translations(company.id, [self.lang], 'name')
        return res
