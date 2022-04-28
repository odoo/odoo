# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        'Description',
        required=True,
    )
    date = fields.Date(
        'Date',
        required=True,
        index=True,
        default=fields.Date.context_today,
    )
    amount = fields.Monetary(
        'Amount',
        required=True,
        default=0.0,
    )
    unit_amount = fields.Float(
        'Quantity',
        default=0.0,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    product_uom_category_id = fields.Many2one(
        related='product_uom_id.category_id',
        string='UoM Category',
        readonly=True,
    )
    account_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        check_company=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.context.get('user_id', self.env.user.id),
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
        store=True,
        compute_sudo=True,
    )
    plan_id = fields.Many2one(
        'account.analytic.plan',
        related='account_id.plan_id',
        store=True,
        readonly=True,
        compute_sudo=True,
    )
    category = fields.Selection(
        [('other', 'Other')],
        default='other',
    )

    @api.constrains('company_id', 'account_id')
    def _check_company_id(self):
        for line in self:
            if line.account_id.company_id and line.company_id.id != line.account_id.company_id.id:
                raise ValidationError(_('The selected account belongs to another company than the one you\'re trying to create an analytic item for'))
