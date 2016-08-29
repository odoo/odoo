# -*- coding: utf-8 -*-
from openerp.osv import fields, orm

from openerp.addons.connector.session import ConnectorSession

from ..unit.import_synchronizer import import_record

class prestashop_product_category(orm.Model):
    _name = 'prestashop.product.category'
    _inherit = 'prestashop.binding'
    _inherits = {'product.category': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'product.category',
            string='Product Category',
            required=True,
            ondelete='cascade'
        ),
        'default_shop_id': fields.many2one('prestashop.shop'),
        'date_add': fields.datetime(
            'Created At (on PrestaShop)',
            readonly=True
        ),
        'date_upd': fields.datetime(
            'Updated At (on PrestaShop)',
            readonly=True
        ),
        'description': fields.char('Description', translate=True),
        'link_rewrite': fields.char('Friendly URL', translate=True),
        'meta_description': fields.char('Meta description', translate=True),
        'meta_keywords': fields.char('Meta keywords', translate=True),
        'meta_title': fields.char('Meta title', translate=True),
    }

class product_product(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.product.product',
            'openerp_id',
            string='PrestaShop Bindings'
        ),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['prestashop_bind_ids'] = []
        return super(product_product, self).copy(
            cr, uid, id, default=default, context=context
        )

    def update_prestashop_quantities(self, cr, uid, ids, context=None):
        for product in self.browse(cr, uid, ids, context=context):
            for prestashop_product in product.prestashop_bind_ids:
                prestashop_product.recompute_prestashop_qty()
            prestashop_combinations = product.prestashop_combinations_bind_ids
            for prestashop_combination in prestashop_combinations:
                prestashop_combination.recompute_prestashop_qty()
        return True


class prestashop_product_product(orm.Model):
    _name = 'prestashop.product.product'
    _inherit = 'prestashop.binding'
    _inherits = {'product.product': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'product.product',
            string='Product',
            required=True,
            ondelete='cascade'
        ),
        # TODO FIXME what name give to field present in
        # prestashop_product_product and product_product
        'always_available': fields.boolean(
            'Active',
            help='if check, this object is always available'),
        'quantity': fields.float(
            'Computed Quantity',
            help="Last computed quantity to send on Prestashop."
        ),
        'description_html': fields.html(
            'Description',
            translate=True,
            help="Description html from prestashop",
        ),
        'description_short_html': fields.html(
            'Short Description',
            translate=True,
        ),
        'date_add': fields.datetime(
            'Created At (on Presta)',
            readonly=True
        ),
        'date_upd': fields.datetime(
            'Updated At (on Presta)',
            readonly=True
        ),
        'default_shop_id': fields.many2one(
            'prestashop.shop',
            'Default shop',
            required=True
        ),
        'link_rewrite': fields.char(
            'Friendly URL',
            translate=True,
            required=False,
        ),
        'combinations_ids': fields.one2many(
            'prestashop.product.combination',
            'main_product_id',
            string='Combinations'
        ),
        'reference': fields.char('Original reference'),
    }

    _sql_constraints = [
        ('prestashop_uniq', 'unique(backend_id, prestashop_id)',
         "A product with the same ID on Prestashop already exists")
    ]

    def recompute_prestashop_qty(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        for product in self.browse(cr, uid, ids, context=context):
            new_qty = self._prestashop_qty(cr, uid, product, context=context)
            self.write(
                cr, uid, product.id,
                {'quantity': new_qty},
                context=context
            )
        return True

    def _prestashop_qty(self, cr, uid, product, context=None):
        if context is None:
            context = {}
        backend = product.backend_id
        stock = backend.warehouse_id.lot_stock_id
        stock_field = 'qty_available'
        location_ctx = context.copy()
        location_ctx['location'] = stock.id
        product_stk = self.read(
            cr, uid, product.id, [stock_field], context=location_ctx
        )
        return product_stk[stock_field]