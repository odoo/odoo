# -*- coding: utf-8 -*-

from openerp import models, fields


class product_template(models.Model):
    """ Add recurrent_invoice field to product template if it is true,
    it will add to related contract.
    """
    _inherit = "product.template"

    recurring_invoice = fields.Boolean(
        string='Recurrent Invoice Product', default=False,
        help="If selected, this product will be added to the "
        "related contract (which must be associated with the SO). \n"
        "It will be used as product for invoice lines and generate "
        "the recurring invoices automatically")
