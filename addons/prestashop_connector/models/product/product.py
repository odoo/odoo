import logging
from openerp.osv import fields, orm

_logger = logging.getLogger(__name__)

class product_template(orm.Model):
    _inherit = 'product.template'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.product.template',
            'openerp_id',
            string='PrestaShop Bindings'
        ),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['prestashop_bind_ids'] = []
        return super(product_template, self).copy(
            cr, uid, id, default=default, context=context
        )

    def update_prestashop_quantities(self, cr, uid, ids, context=None):
        for template in self.browse(cr, uid, ids, context=context):
            for prestashop_template in template.prestashop_bind_ids:
                prestashop_template.recompute_prestashop_qty()
            prestashop_combinations = template.product_variant_ids
            for prestashop_combination in prestashop_combinations:
                prestashop_combination.recompute_prestashop_qty()
        return True


class prestashop_product_template(orm.Model):
    _name = 'prestashop.product.template'
    _inherit = 'prestashop.binding'
    _inherits = {'product.template': 'openerp_id'}
        
    _columns = {
        'openerp_id': fields.many2one(
            'product.template',
            string='Template',
            required=True,
            ondelete='cascade'
        ),
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
        'available_for_order': fields.boolean(
            'Available For Order'
        ),
        'show_price': fields.boolean(
            'Show Price'
        ),
        'combinations_ids': fields.one2many(
            'prestashop.product.combination',
            'main_template_id',
            string='Combinations'
        ),
        'reference': fields.char('Original reference'),
    }

    _defaults = {
        'available_for_order': True,
        'show_price': True,
        'always_available': True
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
        stock_field = backend.quantity_field        
        location_ctx = context.copy()
        location_ctx['location'] = stock.id
        product_stk = self.read(
            cr, uid, product.id, [stock_field], context=location_ctx
        )
        return product_stk[stock_field]
