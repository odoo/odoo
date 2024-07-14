# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.osv import expression


class AccountDisallowedExpensesCategory(models.Model):
    _name = 'account.disallowed.expenses.category'
    _description = "Disallowed Expenses Category"

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the category without removing it.")
    rate_ids = fields.One2many('account.disallowed.expenses.rate', 'category_id', string='Rate')
    company_id = fields.Many2one('res.company')
    account_ids = fields.One2many('account.account', 'disallowed_expenses_category_id', check_company=True)
    current_rate = fields.Char(compute='_compute_current_rate', string='Current Rate')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Disallowed expenses category code should be unique.')
    ]

    @api.depends('current_rate', 'code')
    def _compute_display_name(self):
        for record in self:
            rate = record.current_rate or _('No Rate')
            name = f'{record.code} - {record.name} ({rate})'
            record.display_name = name

    @api.depends('rate_ids')
    def _compute_current_rate(self):
        rates = self._get_current_rates()
        for rec in self:
            rec.current_rate = ('%g%%' % rates[rec.id]) if rates.get(rec.id) else None

    def _get_current_rates(self):
        sql = """
            SELECT
                DISTINCT category_id,
                first_value(rate) OVER (PARTITION BY category_id ORDER BY date_from DESC)
            FROM account_disallowed_expenses_rate
            WHERE date_from < CURRENT_DATE
            AND category_id IN %(ids)s
        """
        self.env.cr.execute(sql, {'ids': tuple(self.ids)})
        return dict(self.env.cr.fetchall())

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            name_domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                name_domain = ['&', '!'] + name_domain[1:]
            domain = expression.AND([name_domain, domain])
        return self._search(domain, limit=limit, order=order)

    def action_read_category(self):
        self.ensure_one()
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.disallowed.expenses.category',
            'res_id': self.id,
        }

class AccountDisallowedExpensesRate(models.Model):
    _name = 'account.disallowed.expenses.rate'
    _description = "Disallowed Expenses Rate"
    _order = 'date_from desc'

    rate = fields.Float(string='Disallowed %', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    category_id = fields.Many2one('account.disallowed.expenses.category', string='Category', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
