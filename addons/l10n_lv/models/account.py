# -*- encoding: utf-8 -*-
##############################################################################
#
#    Part of Odoo.
#    Copyright (C) 2021 Allegro IT (<http://www.allegro.lv/>)
#                       E-mail: <info@allegro.lv>
#                       Address: <Vienibas gatve 109 LV-1058 Riga Latvia>
#                       Phone: +371 67289467
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _
from odoo.http import request

class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _fill_missing_values(self, vals):
        journal_type = vals.get('type')
        if journal_type in ('bank', 'cash') and (not vals.get('default_account_id')):
            company = self.env['res.company'].browse(vals['company_id']) if vals.get('company_id') else self.env.company
            random_account = self.env['account.account'].search([('company_id', '=', company.id)], limit=1)
            digits = len(random_account.code) if random_account else 6
            user_type = self.env.ref('l10n_lv.lv_account_type_2_6')
            if journal_type == 'bank':
                liquidity_account_prefix = company.bank_account_code_prefix or ''
            else:
                liquidity_account_prefix = company.cash_account_code_prefix or company.bank_account_code_prefix or ''
            liquidity_account = self.env['account.account'].create({
                'name': vals.get('name'),
                'code': self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix),
                'user_type_id': user_type.id,
                'currency_id': vals.get('currency_id'),
                'company_id': company.id
            })
            vals.update({
                'default_account_id': liquidity_account.id,
            })
        super(AccountJournal, self)._fill_missing_values(vals)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        self.ensure_one()
        if self == self.env.ref('l10n_lv.l10n_lv_chart_template'):
            sale_tax_rate = 21.0
            purchase_tax_rate = 21.0
        res = super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        if self == self.env.ref('l10n_lv.l10n_lv_chart_template'):
            sale_tax = self.env['account.tax'].search([
                ('type_tax_use','=','sale'), 
                ('amount_type','=','percent'), 
                ('amount','=',21.0), 
                ('company_id','=',company.id)
            ], limit=1)
            if sale_tax and company.account_sale_tax_id != sale_tax:
                company.account_sale_tax_id = sale_tax.id
            purchase_tax = self.env['account.tax'].search([
                ('type_tax_use','=','purchase'), 
                ('amount_type','=','percent'), 
                ('amount','=',21.0), 
                ('company_id','=',company.id)
            ], limit=1)
            if purchase_tax and company.account_purchase_tax_id != purchase_tax:
                company.account_purchase_tax_id = purchase_tax.id
        return res

    # Temporary function for companies using an older version of this module:
    @api.model
    def update_lv_account_group_xml_ids(self):
        self._cr.execute("""UPDATE ir_model_data SET name = CONCAT(ag.company_id, '_', ir_model_data.name), noupdate=True
            FROM account_group AS ag
            WHERE ir_model_data.model = 'account.group'
            AND ir_model_data.res_id = ag.id
            AND ir_model_data.module = 'l10n_lv'""")


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    def _generate_tax(self, company):
        res = super(AccountTaxTemplate, self)._generate_tax(company)
        lv_sale_tax_tmpl = self.env.ref('l10n_lv.lv_tax_template_PVN-SR')
        lv_purchase_tax_tmpl = self.env.ref('l10n_lv.lv_tax_template_Pr-SR')
        IrDefault = self.env['ir.default'].sudo()
        if lv_sale_tax_tmpl and lv_sale_tax_tmpl.id in res['tax_template_to_tax']:
            sale_tax_id = res['tax_template_to_tax'][lv_sale_tax_tmpl.id]
            self.env['ir.config_parameter'].sudo().set_param("account.default_sale_tax_id", sale_tax_id)
            IrDefault.set('product.template', "taxes_id", [sale_tax_id], company_id=company.id)
        if lv_purchase_tax_tmpl and lv_purchase_tax_tmpl.id in res['tax_template_to_tax']:
            purchase_tax_id = res['tax_template_to_tax'][lv_purchase_tax_tmpl.id]
            self.env['ir.config_parameter'].sudo().set_param("account.default_purchase_tax_id", purchase_tax_id)
            IrDefault.set('product.template', "supplier_taxes_id", [purchase_tax_id], company_id=company.id)
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
