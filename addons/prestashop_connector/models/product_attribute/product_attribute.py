from openerp.osv import orm, fields

class product_attribute(orm.Model):
    _inherit = 'product.attribute'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.product.attribute', 'openerp_id',
            string="PrestaShop Bindings"
        ),
        'prestashop_product_attribute_value_bind_ids': fields.one2many(
            'prestashop.product.attribute.value', 'openerp_id',
            string="PrestaShop Product Attribute Value Bindings"
        ),
    }

class prestashop_product_attribute(orm.Model):
    _name='prestashop.product.attribute'
    _inherit = 'prestashop.binding'
    _inherits = {'product.attribute': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'product.attribute',
            string='Product Attribute',
            required=True,
            ondelete='cascade'
        ),
    }

class product_attribute_value(orm.Model):
    _inherit = 'product.attribute.value'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.product.attribute.value', 'openerp_id',
            string="PrestaShop Bindings"
        ),
    }

class prestashop_product_attribute_value(orm.Model):
    _name='prestashop.product.attribute.value'
    _inherit = 'prestashop.binding'
    _inherits = {'product.attribute.value': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'product.attribute.value',
            string='Product Attribute Value',
            required=True,
            ondelete='cascade'
        ),
    }