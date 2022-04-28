# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        check_company=True,
    )
    general_account_id = fields.Many2one(
        'account.account',
        string='Financial Account',
        ondelete='restrict',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        readonly=True,
        related='move_line_id.account_id',
        store=True,
        compute_sudo=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Financial Journal',
        check_company=True,
        readonly=True,
        related='move_line_id.journal_id',
        store=True,
    )
    partner_id = fields.Many2one(
        readonly=False,
        compute="_compute_partner_id",
        store=True,
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Journal Item',
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    code = fields.Char(size=8)
    ref = fields.Char(string='Ref.')
    category = fields.Selection(selection_add=[('invoice', 'Customer Invoice'), ('vendor_bill', 'Vendor Bill')])

    @api.depends('move_line_id')
    def _compute_partner_id(self):
        for line in self:
            line.partner_id = line.move_line_id.partner_id or line.partner_id

    @api.onchange('product_id', 'product_uom_id', 'unit_amount', 'currency_id')
    def on_change_unit_amount(self):
        if not self.product_id:
            return {}

        prod_accounts = self.product_id.product_tmpl_id.with_company(self.company_id)._get_product_accounts()
        unit = self.product_uom_id
        account = prod_accounts['expense']
        if not unit or self.product_id.uom_po_id.category_id.id != unit.category_id.id:
            unit = self.product_id.uom_po_id

        # Compute based on pricetype
        amount_unit = self.product_id.price_compute('standard_price', uom=unit)[self.product_id.id]
        amount = amount_unit * self.unit_amount or 0.0
        result = (self.currency_id.round(amount) if self.currency_id else round(amount, 2)) * -1
        self.amount = result
        self.general_account_id = account
        self.product_uom_id = unit

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get('account_id'):
            return _(
                "Entries: %(account)s",
                account=self.env['account.analytic.account'].browse(self.env.context['account_id']).name
            )
        return super().view_header_get(view_id, view_type)
