# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

ACCOUNT_DOMAIN = [('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance'))]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    property_stock_journal = fields.Many2one(
        'account.journal', "Stock Journal",
        check_company=True,
        compute='_compute_property_stock_account',
        inverse='_set_property_stock_journal')
    property_account_income_categ_id = fields.Many2one(
        'account.account', "Income Account",
        check_company=True,
        domain=ACCOUNT_DOMAIN,
        compute='_compute_property_stock_account',
        inverse='_set_property_account_income_categ_id')
    property_account_expense_categ_id = fields.Many2one(
        'account.account', "Expense Account",
        check_company=True,
        domain=ACCOUNT_DOMAIN,
        compute='_compute_property_stock_account',
        inverse='_set_property_account_expense_categ_id')
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', "Stock Valuation Account",
        check_company=True,
        domain="[('deprecated', '=', False)]",
        compute='_compute_property_stock_account',
        inverse='_set_property_stock_valuation_account_id')
    property_stock_account_input_categ_id = fields.Many2one(
        'account.account', "Stock Input Account",
        check_company=True,
        domain="[('deprecated', '=', False)]",
        compute='_compute_property_stock_account',
        inverse='_set_property_stock_account_input_categ_id')
    property_stock_account_output_categ_id = fields.Many2one(
        'account.account', "Stock Output Account",
        check_company=True,
        domain="[('deprecated', '=', False)]",
        compute='_compute_property_stock_account',
        inverse='_set_property_stock_account_output_categ_id')

    @api.depends('company_id')
    def _compute_property_stock_account(self):
        account_stock_properties_names = self._get_account_stock_properties_names()
        ProductCategory = self.env['product.category']
        for record in self:
            record = record.with_company(record.company_id)
            for fname in account_stock_properties_names:
                field = ProductCategory._fields[fname]
                record[fname] = field.get_company_dependent_fallback(ProductCategory)

    def _set_property_stock_journal(self):
        for record in self:
            record._set_property('property_stock_journal')

    def _set_property_account_income_categ_id(self):
        for record in self:
            record._set_property('property_account_income_categ_id')

    def _set_property_account_expense_categ_id(self):
        for record in self:
            record._set_property('property_account_expense_categ_id')

    def _set_property_stock_valuation_account_id(self):
        for record in self:
            record._set_property('property_stock_valuation_account_id')

    def _set_property_stock_account_input_categ_id(self):
        for record in self:
            record._set_property('property_stock_account_input_categ_id')

    def _set_property_stock_account_output_categ_id(self):
        for record in self:
            record._set_property('property_stock_account_output_categ_id')

    def _set_property(self, field_name):
        self.env['ir.default'].set('product.category', field_name, self[field_name].id, company_id=self.company_id.id)

    @api.model
    def _get_account_stock_properties_names(self):
        return [
            'property_stock_journal',
            'property_account_income_categ_id',
            'property_account_expense_categ_id',
            'property_stock_valuation_account_id',
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
        ]
