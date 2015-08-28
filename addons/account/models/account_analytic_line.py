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
    journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal', required=True, ondelete='restrict', index=True)
    code = fields.Char(size=8)
    ref = fields.Char(string='Ref.')
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', string='Account Currency', store=True, help="The related account currency if not equal to the company one.", readonly=True)
    amount_currency = fields.Monetary(related='move_id.amount_currency', store=True, help="The amount expressed in the related account currency if not equal to the company one.", readonly=True)
    partner_id = fields.Many2one('res.partner', related='account_id.partner_id', string='Partner', store=True)

    # Compute the cost based on the price type define into company
    # property_valuation_price_type property
    @api.v7
    def on_change_unit_amount(self, cr, uid, id, prod_id, quantity, company_id,
            unit=False, journal_id=False, context=None):
        if context is None:
            context = {}
        if not journal_id:
            j_ids = self.pool.get('account.analytic.journal').search(cr, uid, [('type', '=', 'purchase')])
            journal_id = j_ids and j_ids[0] or False
        if not journal_id or not prod_id:
            return {}

        result = 0.0
        journal = self.env['account.analytic.journal'].browse(cr, uid, journal_id, context=context)
        product = self.env['product.product'].browse(cr, uid, prod_id, context=context)
        prod_accounts = product._get_product_accounts()
        unit_obj = False
        if unit:
            unit_obj = self.env['product.uom'].browse(cr, uid, unit, context=context)
        if journal.type != 'sale':
            account = prod_accounts['expense']
            price_type = 'standard_price'
            if not unit_obj or product.uom_po_id.category_id.id != unit_obj.category_id.id:
                unit = product.uom_po_id.id
        else:
            account = prod_accounts['income']
            price_type = 'list_price'
            if not unit_obj or product.uom_id.category_id.id != unit_obj.category_id.id:
                unit = product.uom_id.id

        ctx = context.copy()
        if unit:
            # price_get() will respect a 'uom' in its context, in order
            # to return a default price for those units
            ctx['uom'] = unit
        amount_unit = product.price_get(price_type, context=ctx)[product.id]
        amount = amount_unit * quantity or 0.0
        cur_record = self.browse(cr, uid, id, context=context)
        currency = cur_record.exists() and cur_record.currency_id or product.company_id.currency_id
        result = round(amount, currency.decimal_places)
        if price_type != 'list_price':
            result *= -1
        return {'value': {
            'amount': result,
            'general_account_id': account,
            'product_uom_id': unit
            }
        }

    @api.v8
    @api.onchange('product_id', 'product_uom_id', 'journal_id', 'unit_amount', 'currency_id')
    def on_change_unit_amount(self):
        journal_id = self.journal_id
        if not journal_id:
            journal_id = self.env['account.analytic.journal'].search([('type', '=', 'purchase')], limit=1)
        if not journal_id or not self.product_id:
            return {}

        result = 0.0
        prod_accounts = self.product_id._get_product_accounts()
        unit = self.product_uom_id.id
        if journal_id.type != 'sale':
            account = prod_accounts['expense']
            price_type = 'standard_price'
            if not unit or self.product_id.uom_po_id.category_id.id != unit.category_id.id:
                unit = self.product_id.uom_po_id.id
        else:
            account = prod_accounts['income']
            price_type = 'list_price'
            if not unit or self.product_id.uom_id.category_id.id != unit.category_id.id:
                unit = self.product_id.uom_id.id

        ctx = dict(self._context or {})
        if unit:
            # price_get() will respect a 'uom' in its context, in order
            # to return a default price for those units
            ctx['uom'] = unit

        # Compute based on pricetype
        amount_unit = self.product_id.with_context(ctx).price_get(price_type)[self.product_id.id]
        amount = amount_unit * self.unit_amount
        result = round(amount, self.currency_id.decimal_places)
        if price_type != 'list_price':
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
