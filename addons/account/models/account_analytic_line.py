# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc'

    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    general_account_id = fields.Many2one('account.account', string='Financial Account', ondelete='restrict',
                                         related='move_id.account_id', store=True, domain=[('deprecated', '=', False)])
    move_id = fields.Many2one('account.move.line', string='Move Line', ondelete='cascade', index=True)
    code = fields.Char(size=8)
    ref = fields.Char(string='Ref.')
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', string='Account Currency', store=True, help="The related account currency if not equal to the company one.", readonly=True)
    amount_currency = fields.Monetary(related='move_id.amount_currency', store=True, help="The amount expressed in the related account currency if not equal to the company one.", readonly=True)
    partner_id = fields.Many2one('res.partner', related='account_id.partner_id', string='Partner', store=True)

    @api.v8
    @api.onchange('product_id', 'product_uom_id')
    def on_change_unit_amount(self):
        product_price_type_obj = self.env['product.price.type']
        result = 0.0
        unit = False
        if self.product_id:
            unit = self.product_uom_id.id
            if not self.product_uom_id or self.product_id.uom_id.category_id.id != self.product_uom_id.category_id.id:
                unit = self.product_id.uom_id.id
        account = self.product_id.property_account_income_id.id or self.product_id.categ_id.property_account_income_categ_id.id
        if not account: account = False

        ctx = dict(self._context or {})
        if unit:
            # price_get() will respect a 'uom' in its context, in order
            # to return a default price for those units
            ctx['uom'] = unit

        pricetype = False
        amount_unit = 0.0
        if self.product_id:
            # Compute based on pricetype
            pricetype = product_price_type_obj.search([('field', '=', 'list_price')], limit=1)
            amount_unit = self.product_id.with_context(ctx).price_get(pricetype.field)[self.product_id.id]
        amount = amount_unit * self.unit_amount or 0.0
        result = round(amount, self.currency_id.decimal_places)
        if pricetype and pricetype.field != 'list_price':
            result *= -1
        self.amount = result
        self.general_account_id = account
        self.product_uom_id = unit

    @api.model
    def view_header_get(self, view_id, view_type):
        context = (self._context or {})
        header = False
        if context.get('account_id', False):
            analytic_account = self.env['account.analytic.account'].search([('id', '=', context['account_id'])], limit=1)
            header = _('Entries: ') + (analytic_account.name or '')
        return header
