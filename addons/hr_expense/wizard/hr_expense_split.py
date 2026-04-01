# Part of Odoo. See LICENSE file for full copyright and licensing details.
from copy import deepcopy

from odoo import fields, models, api, Command
from odoo.tools import float_compare

from odoo.addons.hr_expense.models.hr_expense import EXPENSE_APPROVAL_STATE


class HrExpenseSplit(models.TransientModel):
    _name = 'hr.expense.split'
    _inherit = ['analytic.mixin']
    _description = 'Expense Split'
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if 'expense_id' in result:
            expense = self.env['hr.expense'].browse(result['expense_id'])
            result['total_amount_currency'] = 0.0
            result['name'] = expense.name
            result['tax_ids'] = expense.tax_ids
            result['product_id'] = expense.product_id
            result['company_id'] = expense.company_id
            result['analytic_distribution'] = deepcopy(expense.analytic_distribution) or {}
            result['employee_id'] = expense.employee_id
            result['currency_id'] = expense.currency_id
            result['approval_state'] = expense.approval_state
            result['approval_date'] = expense.approval_date
            result['manager_id'] = expense.manager_id
        return result

    name = fields.Char(string='Description', required=True)
    wizard_id = fields.Many2one(comodel_name='hr.expense.split.wizard')
    expense_id = fields.Many2one(comodel_name='hr.expense', string='Expense')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True, check_company=True, domain=[('can_be_expensed', '=', True)],)
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        check_company=True,
        domain="[('type_tax_use', '=', 'purchase')]",
    )
    total_amount_currency = fields.Monetary(
        string="Total In Currency",
        required=True,
        compute='_compute_from_product_id', store=True, readonly=False,
    )
    tax_amount_currency = fields.Monetary(string='Tax amount in Currency', compute='_compute_tax_amount_currency')
    employee_id = fields.Many2one(comodel_name='hr.employee', string="Employee", required=True)
    company_id = fields.Many2one(comodel_name='res.company')
    currency_id = fields.Many2one(comodel_name='res.currency')
    product_has_tax = fields.Boolean(
        string="Whether tax is defined on a selected product",
        compute='_compute_product_has_tax',
    )
    product_has_cost = fields.Boolean(
        string="Is product with non zero cost selected",
        compute='_compute_from_product_id', store=True,
    )
    approval_state = fields.Selection(selection=EXPENSE_APPROVAL_STATE, copy=False, readonly=True)
    approval_date = fields.Datetime(string="Approval Date", readonly=True)
    manager_id = fields.Many2one(
        comodel_name='res.users',
        string="Manager",
        readonly=True,
        domain=lambda self: [('all_group_ids', 'in', self.env.ref('hr_expense.group_hr_expense_team_approver').id)],
    )

    @api.depends('total_amount_currency', 'tax_ids')
    def _compute_tax_amount_currency(self):
        for split in self:
            taxes = split.tax_ids.with_context(force_price_include=True).compute_all(
                price_unit=split.total_amount_currency,
                currency=split.currency_id,
                quantity=1,
                product=split.product_id
            )
            split.tax_amount_currency = taxes['total_included'] - taxes['total_excluded']

    @api.depends('product_id')
    def _compute_from_product_id(self):
        for split in self:
            split.product_has_cost = split.product_id and (float_compare(split.product_id.standard_price, 0.0, precision_digits=2) != 0)
            if split.product_has_cost:
                split.total_amount_currency = split.product_id._price_compute('standard_price', currency=split.currency_id)[split.product_id.id]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        In case we switch to the product without taxes defined on it, taxes should be removed.
        Computed method won't be good for this purpose, as we don't want to recompute and reset taxes in case they are removed on purpose during splitting.
        """
        if self.product_has_tax and self.tax_ids:
            self.tax_ids = self.tax_ids
        else:
            self.tax_ids = self.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.company_id))

    @api.depends('product_id')
    def _compute_product_has_tax(self):
        for split in self:
            split.product_has_tax = split.product_id and split.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(split.company_id))

    def _get_values(self):
        self.ensure_one()
        vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'total_amount_currency': self.total_amount_currency,
            'total_amount': self.expense_id.currency_id.round(self.expense_id.currency_rate * self.total_amount_currency),
            'tax_ids': [Command.set(self.tax_ids.ids)],
            'analytic_distribution': self.analytic_distribution,
            'employee_id': self.employee_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'approval_state': self.approval_state,
            'approval_date': self.approval_date,
            'manager_id': self.manager_id.id,
        }

        account = self.product_id.with_company(self.company_id).product_tmpl_id._get_product_accounts()['expense']
        if account:
            vals['account_id'] = account.id
        return vals
