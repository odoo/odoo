# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api
from openerp.exceptions import UserError


class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'

    def _get_cost_method(self, cr, uid, ids, field, args, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            if product.property_cost_method:
                res[product.id] = product.property_cost_method
            else:
                res[product.id] = product.categ_id.property_cost_method
        return res

    def _get_valuation_type(self, cr, uid, ids, field, args, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            if product.property_valuation:
                res[product.id] = product.property_valuation
            else:
                res[product.id] = product.categ_id.property_valuation
        return res

    def _set_cost_method(self, cr, uid, ids, name, value, arg, context=None):
        return self.write(cr, uid, ids, {'property_cost_method': value}, context=context)

    def _set_valuation_type(self, cr, uid, ids, name, value, arg, context=None):
        return self.write(cr, uid, ids, {'property_valuation': value}, context=context)

    _columns = {
        'property_valuation': fields.property(type='selection', selection=[('manual_periodic', 'Periodic (manual)'),
                                        ('real_time', 'Perpetual (automated)')], string='Inventory Valuation',
                                        help="If perpetual valuation is enabled for a product, the system will automatically create journal entries corresponding to stock moves, with product price as specified by the 'Costing Method'" \
                                             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products."
                                        , copy=True),
        'valuation': fields.function(_get_valuation_type, fnct_inv=_set_valuation_type, type='char'),  # TDE FIXME: store it ?
        'property_cost_method': fields.property(type='selection', selection=[('standard', 'Standard Price'), ('average', 'Average Price'), ('real', 'Real Price')],
            help="""Standard Price: The cost price is manually updated at the end of a specific period (usually once a year).
                    Average Price: The cost price is recomputed at each incoming shipment and used for the product valuation.
                    Real Price: The cost price displayed is the price of the last outgoing product (will be use in case of inventory loss for example).""",
            string="Costing Method", copy=True),
        'cost_method': fields.function(_get_cost_method, fnct_inv=_set_cost_method, type='char'),  # TDE FIXME: store it ?
        'property_stock_account_input': fields.property(
            type='many2one',
            relation='account.account',
            string='Stock Input Account',
            domain=[('deprecated', '=', False)],
            help="When doing real-time inventory valuation, counterpart journal items for all incoming stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the source location. When not set on the product, the one from the product category is used."),
        'property_stock_account_output': fields.property(
            type='many2one',
            relation='account.account',
            string='Stock Output Account',
            domain=[('deprecated', '=', False)],
            help="When doing real-time inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the destination location. When not set on the product, the one from the product category is used."),
    }

    _defaults = {
        'property_valuation': 'manual_periodic',
    }

    def create(self, cr, uid, vals, context=None):
        if vals.get('cost_method'):
            vals['property_cost_method'] = vals.pop('cost_method')
        if vals.get('valuation'):
            vals['property_valuation'] = vals.pop('valuation')
        return super(product_template, self).create(cr, uid, vals, context=context)

    @api.onchange('type')
    def onchange_type_valuation(self):
        if self.type != 'product':
            self.valuation = 'manual_periodic'
        return {}

    @api.multi
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(product_template, self)._get_product_accounts()
        accounts.update({
            'stock_input': self.property_stock_account_input or self.categ_id.property_stock_account_input_categ_id,
            'stock_output': self.property_stock_account_output or self.categ_id.property_stock_account_output_categ_id,
            'stock_valuation': self.categ_id.property_stock_valuation_account_id or False,
        })
        return accounts

    @api.multi
    def get_product_accounts(self, fiscal_pos=None):
        """ Add the stock journal related to product to the result of super()
        @return: dictionary which contains all needed information regarding stock accounts and journal and super (income+expense accounts)
        """
        accounts = super(product_template, self).get_product_accounts(fiscal_pos=fiscal_pos)
        accounts.update({'stock_journal': self.categ_id.property_stock_journal or False})
        return accounts

    # To remove in master because this function is now used on "product.product" model.
    def do_change_standard_price(self, cr, uid, ids, new_price, context=None):
        """ Changes the Standard Price of Product and creates an account move accordingly."""
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        user_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        loc_ids = location_obj.search(cr, uid, [('usage', '=', 'internal'), ('company_id', '=', user_company_id)])
        for rec_id in ids:
            datas = self.get_product_accounts(cr, uid, rec_id, context=context)
            for location in location_obj.browse(cr, uid, loc_ids, context=context):
                c = context.copy()
                c.update({'location': location.id, 'compute_child': False})
                product = self.browse(cr, uid, rec_id, context=c)

                diff = product.standard_price - new_price
                if not diff:
                    raise UserError(_("No difference between standard price and new price!"))
                for prod_variant in product.product_variant_ids:
                    qty = prod_variant.qty_available
                    if qty:
                        # Accounting Entries
                        amount_diff = abs(diff * qty)
                        if diff * qty > 0:
                            debit_account_id = datas['expense'].id
                            credit_account_id = datas['stock_valuation'].id
                        else:
                            debit_account_id = datas['stock_valuation'].id
                            credit_account_id = datas['expense'].id

                        lines = [(0, 0, {'name': _('Standard Price changed'),
                                        'account_id': debit_account_id,
                                        'debit': amount_diff,
                                        'credit': 0,
                                        }),
                                 (0, 0, {
                                        'name': _('Standard Price changed'),
                                        'account_id': credit_account_id,
                                        'debit': 0,
                                        'credit': amount_diff,
                                        })]
                        move_vals = {
                            'journal_id': datas['stock_journal'].id,
                            'company_id': location.company_id.id,
                            'line_ids': lines,
                        }
                        move_id = move_obj.create(cr, uid, move_vals, context=context)
                        move_obj.post(cr, uid, [move_id], context=context)
            self.write(cr, uid, rec_id, {'standard_price': new_price})
        return True


class product_product(osv.osv):
    _inherit = 'product.product'

    @api.onchange('type')
    def onchange_type_valuation(self):
        if self.type != 'product':
            self.valuation = 'manual_periodic'
        return {}

    def do_change_standard_price(self, cr, uid, ids, new_price, context=None):
        """ Changes the Standard Price of Product and creates an account move accordingly."""
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        user_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        loc_ids = location_obj.search(cr, uid, [('usage', '=', 'internal'), ('company_id', '=', user_company_id)])
        for rec_id in ids:
            for location in location_obj.browse(cr, uid, loc_ids, context=context):
                c = context.copy()
                c.update({'location': location.id, 'compute_child': False})
                product = self.browse(cr, uid, rec_id, context=c)
                datas = self.pool['product.template'].get_product_accounts(cr, uid, product.product_tmpl_id.id, context=context)
                diff = product.standard_price - new_price
                if not diff:
                    raise UserError(_("No difference between standard price and new price!"))
                qty = product.qty_available
                if qty:
                    # Accounting Entries
                    amount_diff = abs(diff * qty)
                    if diff * qty > 0:
                        debit_account_id = datas['expense'].id
                        credit_account_id = datas['stock_valuation'].id
                    else:
                        debit_account_id = datas['stock_valuation'].id
                        credit_account_id = datas['expense'].id

                    lines = [(0, 0, {'name': _('Standard Price changed'),
                                    'account_id': debit_account_id,
                                    'debit': amount_diff,
                                    'credit': 0,
                                    }),
                             (0, 0, {
                                    'name': _('Standard Price changed'),
                                    'account_id': credit_account_id,
                                    'debit': 0,
                                    'credit': amount_diff,
                                    })]
                    move_vals = {
                        'journal_id': datas['stock_journal'].id,
                        'company_id': location.company_id.id,
                        'line_ids': lines,
                    }
                    move_id = move_obj.create(cr, uid, move_vals, context=context)
                    move_obj.post(cr, uid, [move_id], context=context)
            self.write(cr, uid, rec_id, {'standard_price': new_price})
        return True

class product_category(osv.osv):
    _inherit = 'product.category'
    _columns = {
        'property_valuation': fields.property(
            type='selection',
            selection=[('manual_periodic', 'Periodic (manual)'),
                       ('real_time', 'Perpetual (automated)')],
            string='Inventory Valuation',
            required=True, copy=True,
            help="If perpetual valuation is enabled for a product, the system "
                 "will automatically create journal entries corresponding to "
                 "stock moves, with product price as specified by the 'Costing "
                 "Method'. The inventory variation account set on the product "
                 "category will represent the current inventory value, and the "
                 "stock input and stock output account will hold the counterpart "
                 "moves for incoming and outgoing products."),
        'property_cost_method': fields.property(
            type='selection',
            selection=[('standard', 'Standard Price'),
                       ('average', 'Average Price'),
                       ('real', 'Real Price')],
            string="Costing Method",
            required=True, copy=True,
            help="Standard Price: The cost price is manually updated at the end "
                 "of a specific period (usually once a year).\nAverage Price: "
                 "The cost price is recomputed at each incoming shipment and "
                 "used for the product valuation.\nReal Price: The cost price "
                 "displayed is the price of the last outgoing product (will be "
                 "used in case of inventory loss for example)."""),
        'property_stock_journal': fields.property(
            relation='account.journal',
            type='many2one',
            string='Stock Journal',
            help="When doing real-time inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed."),
        'property_stock_account_input_categ_id': fields.property(
            type='many2one',
            relation='account.account',
            string='Stock Input Account',
            domain=[('deprecated', '=', False)], oldname="property_stock_account_input_categ",
            help="When doing real-time inventory valuation, counterpart journal items for all incoming stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the source location. This is the default value for all products in this category. It "
                 "can also directly be set on each product"),
        'property_stock_account_output_categ_id': fields.property(
            type='many2one',
            relation='account.account',
            domain=[('deprecated', '=', False)],
            string='Stock Output Account', oldname="property_stock_account_output_categ",
            help="When doing real-time inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account, unless "
                 "there is a specific valuation account set on the destination location. This is the default value for all products in this category. It "
                 "can also directly be set on each product"),
        'property_stock_valuation_account_id': fields.property(
            type='many2one',
            relation='account.account',
            string="Stock Valuation Account",
            domain=[('deprecated', '=', False)],
            help="When real-time inventory valuation is enabled on a product, this account will hold the current value of the products.",),
    }
