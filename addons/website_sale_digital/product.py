from openerp import models, fields, api, _


class product_template(models.Model):
    _inherit = ['product.template']

    digital_content = fields.Boolean('Digital Content', help="If checked, it will allow clients to download the product attachments when they have bought it.")
