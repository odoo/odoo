# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import Warning


class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc'

    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    general_account_id = fields.Many2one('account.account', string='Financial Account', required=True, ondelete='restrict', domain=[('deprecated', '=', False)])
    move_id = fields.Many2one('account.move.line', string='Move Line', ondelete='cascade', index=True)
    journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal', required=True, ondelete='restrict', index=True)
    code = fields.Char(string='Code', size=8)
    ref = fields.Char(string='Ref.')
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', string='Account Currency', store=True, help="The related account currency if not equal to the company one.", readonly=True)
    amount_currency = fields.Float(related='move_id.amount_currency', string='Amount Currency', store=True, help="The amount expressed in the related account currency if not equal to the company one.", readonly=True)
    partner_id = fields.Many2one('res.partner', related='account_id.partner_id', string='Partner', store=True)

# NOTE: Commented the code because 'company_id' field is not there and its comes from inherited model. Here field inheritance is not supported
# company_id = fields.Many2one(default=lambda self: self.env['res.company']._company_default_get('account.analytic.line')) 
#     _defaults = {
#         'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.analytic.line', context=c),
#     }

    # Compute the cost based on the price type define into company
    # property_valuation_price_type property
    @api.v7
    def on_change_unit_amount(self, cr, uid, id, prod_id, quantity, company_id,
            unit=False, journal_id=False, context=None):
        if context==None:
            context={}
        if not journal_id:
            j_ids = self.pool.get('account.analytic.journal').search(cr, uid, [('type','=','purchase')])
            journal_id = j_ids and j_ids[0] or False
        if not journal_id or not prod_id:
            return {}
        product_obj = self.pool.get('product.product')
        analytic_journal_obj =self.pool.get('account.analytic.journal')
        product_price_type_obj = self.pool.get('product.price.type')
        product_uom_obj = self.pool.get('product.uom')
        j_id = analytic_journal_obj.browse(cr, uid, journal_id, context=context)
        prod = product_obj.browse(cr, uid, prod_id, context=context)
        result = 0.0
        if prod_id:
            unit_obj = False
            if unit:
                unit_obj = product_uom_obj.browse(cr, uid, unit, context=context)
            if not unit_obj or prod.uom_id.category_id.id != unit_obj.category_id.id:
                unit = prod.uom_id.id
            if j_id.type == 'purchase':
                if not unit_obj or prod.uom_po_id.category_id.id != unit_obj.category_id.id:
                    unit = prod.uom_po_id.id
        if j_id.type <> 'sale':
            a = prod.property_account_expense.id
            if not a:
                a = prod.categ_id.property_account_expense_categ.id
            if not a:
                raise Warning(_('There is no expense account defined ' \
                                'for this product: "%s" (id:%d).') % \
                                (prod.name, prod.id,))
        else:
            a = prod.property_account_income.id
            if not a:
                a = prod.categ_id.property_account_income_categ.id
            if not a:
                raise Warning(_('There is no income account defined ' \
                                'for this product: "%s" (id:%d).') % \
                                (prod.name, prod_id,))
 
        flag = False
        # Compute based on pricetype
        product_price_type_ids = product_price_type_obj.search(cr, uid, [('field','=','standard_price')], context=context)
        pricetype = product_price_type_obj.browse(cr, uid, product_price_type_ids, context=context)[0]
        if journal_id:
            journal = analytic_journal_obj.browse(cr, uid, journal_id, context=context)
            if journal.type == 'sale':
                product_price_type_ids = product_price_type_obj.search(cr, uid, [('field','=','list_price')], context=context)
                if product_price_type_ids:
                    pricetype = product_price_type_obj.browse(cr, uid, product_price_type_ids, context=context)[0]
        # Take the company currency as the reference one
        if pricetype.field == 'list_price':
            flag = True
        ctx = context.copy()
        if unit:
            # price_get() will respect a 'uom' in its context, in order
            # to return a default price for those units
            ctx['uom'] = unit
        amount_unit = prod.price_get(pricetype.field, context=ctx)[prod.id]
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        amount = amount_unit * quantity or 0.0
        result = round(amount, prec)
        if not flag:
            result *= -1
        return {'value': {
            'amount': result,
            'general_account_id': a,
            'product_uom_id': unit
            }
        }

    @api.v8
    @api.multi
    @api.onchange('product_id','product_uom_id')
    def on_change_unit_amount(self):
        product_price_type_obj = self.env['product.price.type']

        journal_id = self.journal_id
        if not journal_id:
            journal_id = self.env['account.analytic.journal'].search([('type','=','purchase')], limit=1)
        if not journal_id or not self.product_id:
            return {}

        result = 0.0
        if self.product_id:
            unit = self.product_uom_id.id
            if not self.product_uom_id or self.product_id.uom_id.category_id.id != self.product_uom_id.category_id.id:
                unit = self.product_id.uom_id.id
            if journal_id.type == 'purchase':
                if not self.product_uom_id or self.product_id.uom_po_id.category_id.id != self.product_uom_id.category_id.id:
                    unit = self.product_id.uom_po_id.id
        if journal_id.type != 'sale':
            account = self.product_id.property_account_expense.id or self.product_id.categ_id.property_account_expense_categ.id
            if not account:
                raise Warning(_('There is no expense account defined ' \
                                'for this product: "%s" (id:%d).') % \
                                (self.product_id.name, self.product_id.id,))
        else:
            account = self.product_id.property_account_income.id or self.product_id.categ_id.property_account_income_categ.id
            if not account:
                raise Warning(_('There is no income account defined ' \
                                'for this product: "%s" (id:%d).') % \
                                (self.product_id.name, self.product_id.id,))

        # Compute based on pricetype
        if journal_id.type == 'sale':
            pricetype = product_price_type_obj.search([('field','=','list_price')], limit=1)
        else:
            pricetype = product_price_type_obj.search([('field','=','standard_price')], limit=1)

        ctx = dict(self._context or {})
        if unit:
            # price_get() will respect a 'uom' in its context, in order
            # to return a default price for those units
            ctx['uom'] = unit
        amount_unit = self.product_id.with_context(ctx).price_get(pricetype.field)[self.product_id.id]
        prec = self.env['decimal.precision'].precision_get('Account')
        amount = amount_unit * self.unit_amount or 0.0
        result = round(amount, prec)
        if pricetype.field != 'list_price':
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


class res_partner(models.Model):
    """ Inherits partner and adds contract information in the partner form """
    _inherit = 'res.partner'

    contract_ids = fields.One2many('account.analytic.account', 'partner_id', string='Contracts', readonly=True)
