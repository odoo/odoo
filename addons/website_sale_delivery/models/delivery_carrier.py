from openerp.osv import orm, fields


class delivery_carrier(orm.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.mixin']

    _columns = {
        'website_description': fields.related('product_id', 'description_sale', type="text", string='Description for Online Quotations'),
    }
    _defaults = {
        'website_published': False
    }
