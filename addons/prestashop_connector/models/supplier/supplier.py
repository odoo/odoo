from openerp.osv import fields, orm

from openerp.addons.connector.session import ConnectorSession

from ..unit.import_synchronizer import import_record


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'prestashop_supplier_bind_ids': fields.one2many(
            'prestashop.supplier',
            'openerp_id',
            string="Prestashop supplier bindings",
        ),
    }


class prestashop_supplier(orm.Model):
    _name = 'prestashop.supplier'
    _inherit = 'prestashop.binding'
    _inherits = {'res.partner': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'res.partner',
            string='Partner',
            required=True,
            ondelete='cascade'
        ),
    }


class product_supplierinfo(orm.Model):
    _inherit = 'product.supplierinfo'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.product.supplierinfo',
            'openerp_id',
            string="Prestashop bindings",
        ),
    }


class prestashop_product_supplierinfo(orm.Model):
    _name = 'prestashop.product.supplierinfo'
    _inherit = 'prestashop.binding'
    _inherits = {'product.supplierinfo': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'product.supplierinfo',
            string='Supplier info',
            required=True,
            ondelete='cascade'
        ),
    }
