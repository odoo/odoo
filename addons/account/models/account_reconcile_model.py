# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountReconcileModel(models.Model):
    _name = "account.reconcile.model"
    _description = "Preset to create journal entries during a invoices and payments matching"

    # Base fields.
    name = fields.Char(string='Button Label', required=True)
    sequence = fields.Integer(required=True, default=10)
    has_second_line = fields.Boolean(string='Add a second line', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    # First part fields.
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of balance')
        ], required=True, default='percentage')
    is_tax_price_included = fields.Boolean(string='Is Tax Included in Price', related='tax_id.price_include',
        help='Technical field used inside the view to make the force_tax_included field readonly if the tax is already price included.')
    tax_amount_type = fields.Selection(string='Tax Amount Type', related='tax_id.amount_type',
        help='Technical field used inside the view to make the force_tax_included field invisible if the tax is a group.')
    force_tax_included = fields.Boolean(string='Tax Included in Price',
        help='Force the tax to be managed as a price included tax.')
    amount = fields.Float(digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    # Second part fields.
    second_account_id = fields.Many2one('account.account', string='Second Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    second_journal_id = fields.Many2one('account.journal', string='Second Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    second_label = fields.Char(string='Second Journal Item Label')
    second_amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of amount')
        ], string="Second Amount type",required=True, default='percentage')
    is_second_tax_price_included = fields.Boolean(string='Is Second Tax Included in Price', related='second_tax_id.price_include',
        help='Technical field used inside the view to make the force_second_tax_included field readonly if the tax is already price included.')
    second_tax_amount_type = fields.Selection(string='Second Tax Amount Type', related='second_tax_id.amount_type',
        help='Technical field used inside the view to make the force_second_tax_included field invisible if the tax is a group.')
    force_second_tax_included = fields.Boolean(string='Second Tax Included in Price',
        help='Force the second tax to be managed as a price included tax.')
    second_amount = fields.Float(string='Second Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    second_tax_id = fields.Many2one('account.tax', string='Second Tax', ondelete='restrict', domain=[('type_tax_use', '=', 'purchase')])
    second_analytic_account_id = fields.Many2one('account.analytic.account', string='Second Analytic Account', ondelete='set null')
    second_analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Second Analytic Tags')

    @api.onchange('name')
    def onchange_name(self):
        self.label = self.name

    @api.onchange('tax_id')
    def _onchange_tax_id(self):
        if self.tax_id:
            self.force_tax_included = self.tax_id.price_include

    @api.onchange('second_tax_id')
    def _onchange_second_tax_id(self):
        if self.second_tax_id:
            self.force_second_tax_included = self.second_tax_id.price_include
