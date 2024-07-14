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
        for record in self:
            properties = self.env['ir.property'].sudo().search([
                ('name', 'in', account_stock_properties_names),
                ('company_id', '=', record.company_id.id),
                ('res_id', '=', False),
            ])
            for field in account_stock_properties_names:
                stock_property = properties.filtered(lambda p: p.name == field)
                if stock_property and stock_property.value_reference:
                    model, record_id = stock_property.value_reference.split(',')
                    value = self.env[model].search([('id', '=', record_id)])
                    record[field] = value
                else:
                    record[field] = False

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
        self.env['ir.property']._set_default(
            field_name,
            'product.category',
            self[field_name],
            self.company_id,
        )

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
