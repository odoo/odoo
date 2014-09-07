from openerp.osv import fields, osv

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'digital_content': fields.boolean('Digital Content', help="If checked, it will allow clients to download the product attachments when they have bought it."),
    }