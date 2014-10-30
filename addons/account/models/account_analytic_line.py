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

#     _defaults = {
#         'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.analytic.line', context=c),
#     }

    @api.multi
    def _check_company(self):
        for line in self:
            if line.move_id and not line.account_id.company_id.id == line.move_id.account_id.company_id.id:
                return False
        return True

    # Compute the cost based on the price type define into company
    # property_valuation_price_type property
    @api.multi
    def on_change_unit_amount(self, prod_id, quantity, company_id, unit=False, journal_id=False):
        analytic_journal_obj = self.env['account.analytic.journal']
        product_price_type_obj = self.env['product.price.type']

        if not journal_id:
            j_ids = analytic_journal_obj.search([('type','=','purchase')])
            journal_id = j_ids.ids and j_ids.ids[0] or False
        if not journal_id or not prod_id:
            return {}

        j_id = analytic_journal_obj.browse(journal_id)
        prod = self.env['product.product'].browse(prod_id)
        result = 0.0
        if prod_id:
            unit_obj = False
            if unit:
                unit_obj = self.env['product.uom'].browse(unit)
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
        pricetype = product_price_type_obj.search([('field','=','standard_price')])
        if j_id.type == 'sale':
            product_price_type_ids = product_price_type_obj.search([('field','=','list_price')])
            if product_price_type_ids:
                pricetype = product_price_type_ids
        # Take the company currency as the reference one
        if pricetype.field == 'list_price':
            flag = True
        ctx = self._context.copy()
        if unit:
            # price_get() will respect a 'uom' in its context, in order
            # to return a default price for those units
            ctx['uom'] = unit
        amount_unit = prod.with_context(ctx).price_get(pricetype.field)[prod.id]
        prec = self.env['decimal.precision'].precision_get('Account')
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
