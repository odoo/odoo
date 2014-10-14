# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _

class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc'

    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    general_account_id = fields.Many2one('account.account', string='Financial Account', required=True, ondelete='restrict', domain=[('deprecated', '=', False)])
    move_id = fields.Many2one('account.move.line', string='Move Line', ondelete='cascade', index=True)
    journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal', required=True, ondelete='restrict', index=True),
    code = fields.Char(string='Code', size=8)
    ref = fields.Char(string='Ref.')
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', string='Account Currency', store=True, help="The related account currency if not equal to the company one.", readonly=True)
    amount_currency = fields.Float(related='move_id.amount_currency', string='Amount Currency', store=True, help="The amount expressed in the related account currency if not equal to the company one.", readonly=True)
    partner_id = fields.Many2one('res.partner', related='account_id.partner_id', string='Partner', store=True)

    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.analytic.line', context=c),
    }

    def _check_company(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.move_id and not l.account_id.company_id.id == l.move_id.account_id.company_id.id:
                return False
        return True

    # Compute the cost based on the price type define into company
    # property_valuation_price_type property
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
                raise osv.except_osv(_('Error!'),
                        _('There is no expense account defined ' \
                                'for this product: "%s" (id:%d).') % \
                                (prod.name, prod.id,))
        else:
            a = prod.property_account_income.id
            if not a:
                a = prod.categ_id.property_account_income_categ.id
            if not a:
                raise osv.except_osv(_('Error!'),
                        _('There is no income account defined ' \
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

    @api.model
    def view_header_get(self, view_id, view_type):
        context = dict(self._context or {})
        if context.get('account_id', False):
            # account_id in context may also be pointing to an account.account.id
            self._cr.execute('select name from account_analytic_account where id=%s', (context['account_id'],))
            res = self._cr.fetchone()
            if res:
                res = _('Entries: ')+ (res[0] or '')
            return res
        return False


class res_partner(models.Model):
    """ Inherits partner and adds contract information in the partner form """
    _inherit = 'res.partner'

    contract_ids = fields.One2many('account.analytic.account', 'partner_id', string='Contracts', readonly=True)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
