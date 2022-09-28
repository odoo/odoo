# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools import float_compare


class HrExpenseSplit(models.TransientModel):

    _name = 'hr.expense.split'
    _inherit = ['analytic.mixin']
    _description = 'Expense Split'

    def default_get(self, fields):
        result = super(HrExpenseSplit, self).default_get(fields)
        if 'expense_id' in result:
            expense = self.env['hr.expense'].browse(result['expense_id'])
            result['total_amount'] = 0.0
            result['name'] = expense.name
            result['tax_ids'] = expense.tax_ids
            result['product_id'] = expense.product_id
            result['company_id'] = expense.company_id
            result['analytic_distribution'] = expense.analytic_distribution
            result['employee_id'] = expense.employee_id
            result['currency_id'] = expense.currency_id
        return result

    name = fields.Char('Description', required=True)
    wizard_id = fields.Many2one('hr.expense.split.wizard')
    expense_id = fields.Many2one('hr.expense', string='Expense')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    tax_ids = fields.Many2many('account.tax', domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]")
    total_amount = fields.Monetary("Total In Currency", required=True, compute='_compute_from_product_id', store=True, readonly=False)
    amount_tax = fields.Monetary(string='Tax amount in Currency', compute='_compute_amount_tax')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency')
    product_has_tax = fields.Boolean("Whether tax is defined on a selected product", compute='_compute_product_has_tax')
    product_has_cost = fields.Boolean("Is product with non zero cost selected", compute='_compute_from_product_id', store=True)

    @api.depends('total_amount', 'tax_ids')
    def _compute_amount_tax(self):
        for split in self:
            taxes = split.tax_ids.with_context(force_price_include=True).compute_all(price_unit=split.total_amount, currency=split.currency_id, quantity=1, product=split.product_id)
            split.amount_tax = taxes['total_included'] - taxes['total_excluded']

    @api.depends('product_id')
    def _compute_from_product_id(self):
        for split in self:
            split.product_has_cost = split.product_id and (float_compare(split.product_id.standard_price, 0.0, precision_digits=2) != 0)
            if split.product_has_cost:
                split.total_amount = split.product_id.price_compute('standard_price', currency=split.currency_id)[split.product_id.id]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        In case we switch to the product without taxes defined on it, taxes should be removed.
        Computed method won't be good for this purpose, as we don't want to recompute and reset taxes in case they are removed on purpose during splitting.
        """
        self.tax_ids = self.tax_ids if self.product_has_tax and self.tax_ids else self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.company_id)

    @api.depends('product_id')
    def _compute_product_has_tax(self):
        for split in self:
            split.product_has_tax = split.product_id and split.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == split.company_id)

    def _get_values(self):
        self.ensure_one()
        vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'total_amount': self.total_amount,
            'tax_ids': self.tax_ids.ids,
            'analytic_distribution': self.analytic_distribution,
            'employee_id': self.employee_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'unit_amount': self.product_id.price_compute('standard_price', currency=self.currency_id)[self.product_id.id]
        }

        account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
        if account:
            vals['account_id'] = account.id
        return vals
