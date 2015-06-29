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
    @api.onchange('product_id', 'unit_amount', 'company_id', 'product_uom_id', 'journal_id')
    def on_change_unit_amount_wrapper(self):
        self.ensure_one()
        values = self.on_change_unit_amount(self.product_id.id, self.unit_amount, self.company_id.id, self.product_uom_id.id, self.journal_id.id)
        if values and values['value']:
            for fname, value in values['value'].iteritems():
                setattr(self, fname, value)

    @api.multi
    def on_change_unit_amount(self, product_id, unit_amount, company_id, product_uom_id, journal_id):

        journal_id = self.journal_id
        if not journal_id:
            journal_id = self.env['account.analytic.journal'].search([('type', '=', 'purchase')], limit=1)
        if not journal_id or not product_id:
            return {}
        ProductUom = self.env['product.uom']
        Product = self.env['product.product']

        result = 0.0
        unit = False
        if self.product_id:
            unit = self.product_uom_id.id
            if not self.product_uom_id or self.product_id.uom_id.category_id.id != self.product_uom_id.category_id.id:
                unit = self.product_id.uom_id.id
        if product_id:
            if product_uom_id:
                unit = ProductUom.browse(product_uom_id)
            prod = Product.browse(product_id)
            if not product_uom_id or prod.uom_id.category_id.id != unit.category_id.id:
                unit = prod.uom_id
            if journal_id.type == 'purchase':
                if not unit or prod.uom_po_id.category_id.id != unit.category_id.id:
                    unit = self.product_id.uom_po_id
        if journal_id.type != 'sale':
            account = prod.property_account_expense_id.id or prod.categ_id.property_account_expense_categ_id.id
            if not account:
                raise UserError(_('There is no expense account defined ' \
                                'for this product: "%s" (id:%d).') % \
                                (prod.name, prod.id,))
        else:
            account = prod.property_account_income_id.id or prod.categ_id.property_account_income_categ_id.id
            if not account:
                raise UserError(_('There is no income account defined ' \
                                'for this product: "%s" (id:%d).') % \
                                (prod.name, prod.id,))
        flag = False
        # Compute based on pricetype
        amount_unit = 0.0
        if journal_id.type == 'sale':
            base_on = 'list_price'
        else:
            base_on = 'standard_price'

        ctx = dict(self._context or {})

        if base_on == 'list_price':
            flag = True
        if unit:
            # price_get() will respect a 'uom' in its context, in order
            # to return a default price for those units
            ctx['uom'] = unit
        amount_unit = prod.price_get(base_on)
        if amount_unit:
            amount_unit = amount_unit[prod.id]
        else:
            amount_unit = 0.0
        amount = amount_unit * unit_amount or 0.0
        currency = prod.company_id.currency_id
        result = round(amount, currency.decimal_places)
        if not flag:
            result *= -1
        return {'value': {
            'amount': result,
            'general_account_id': account,
            'product_uom_id': unit
            }
        }

    @api.model
    def view_header_get(self, view_id, view_type):
        context = (self._context or {})
        header = False
        if context.get('account_id', False):
            analytic_account = self.env['account.analytic.account'].search([('id', '=', context['account_id'])], limit=1)
            header = _('Entries: ') + (analytic_account.name or '')
        return header
