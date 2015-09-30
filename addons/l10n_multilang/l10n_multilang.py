# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
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
            for element in in_ids:
                if value[element.id]:
                    #copy Translation from Source to Destination object
                    xlat_obj.create({
                        'name': out_ids._name + ',' + in_field,
                        'type': 'model',
                        'res_id': out_ids[counter].id,
                        'lang': lang,
                        'src': element.name,
                        'value': value[element.id],
                    })
                else:
                    _logger.info('Language: %s. Translation from template: there is no translation available for %s!' %(lang,  element.name))
                counter += 1
        return True

    @api.multi
    def process_coa_translations(self):
        installed_lang_ids = self.env['res.lang'].search([])
        installed_langs = [x.code for x in installed_lang_ids]
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
                        # copy account.tax translations
                        chart_template_id._process_taxes_translations(company.id, langs, 'name')
                        # copy account.fiscal.position translations
                        chart_template_id._process_fiscal_pos_translations(company.id, langs, 'name')
        return True

    @api.multi
    def _process_accounts_translations(self, company_id, langs, field):
        in_ids = self.env['account.account.template'].search([('chart_template_id', '=', self.id)], order='id')
        out_ids = self.env['account.account'].search([('company_id', '=', company_id)], order='id')
        return self.process_translations(langs, field, in_ids, out_ids)

    @api.multi
    def _process_taxes_translations(self, company_id, langs, field):
        in_ids = self.env['account.tax.template'].search([('chart_template_id', '=', self.id)], order='id')
        out_ids = self.env['account.tax'].search([('company_id', '=', company_id)], order='id')
        return self.process_translations(langs, field, in_ids, out_ids)

    @api.multi
    def _process_fiscal_pos_translations(self, company_id, langs, field):
        in_ids = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)], order='id')
        out_ids = self.env['account.fiscal.position'].search([('company_id', '=', company_id)], order='id')
        return self.process_translations(langs, field, in_ids, out_ids)
