from odoo import api, fields, models, _

class Product(models.Model):
    _inherit = "product.template"

    l10n_ec_auto_witholding = fields.Boolean(_('Automate witholdings'))