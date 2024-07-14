import logging

from odoo import models, fields, api
from odoo.tools.float_utils import float_repr

_logger = logging.getLogger(__name__)

PRICER_RELATED_FIELDS = [
    'name',
    'list_price',
    'barcode',
    'taxes_id',
    'currency_id',
    'pricer_tag_ids',
    'pricer_store_id',
]

class PricerProductTemplate(models.Model):
    """ Adding the necessary fields to products to use with Pricer electronic tags """
    _inherit = 'product.template'

    pricer_store_id = fields.Many2one(
        comodel_name='pricer.store',
        string='Pricer Store',
        help='This product will be linked to and displayed on the Pricer tags of the store selected here'
    )
    pricer_tag_ids = fields.One2many(
        comodel_name='pricer.tag',
        inverse_name='product_id',
        string='Pricer tags ids',
        help='This product will be linked to and displayed on the Pricer tags with ids listed here. It is recommended to use a barcode scanner'
    )

    # Boolean to checker whether we need to create/update this product in Pricer db
    pricer_product_to_create_or_update = fields.Boolean(default=False)

    # String representing price including taxes
    # Used in requests sent to the Pricer API and displayed on tags
    pricer_display_price = fields.Char(compute='_compute_pricer_display_price')

    @api.depends('list_price')
    def _compute_pricer_display_price(self):
        """
        Sets pricer_display_price to the price including customer taxes if any
        If there are no customer taxes pricer_display_price will be set to the amount excluding taxes
        """
        for record in self:
            currency = record.currency_id
            price = record.list_price
            if not record.taxes_id:
                record.pricer_display_price = float_repr(price, currency.decimal_places)
            else:
                res = record.taxes_id.compute_all(price, product=record, partner=record.env['res.partner'])
                rounded_including = float_repr(res['total_included'], currency.decimal_places)
                rounded_excluding = float_repr(res['total_excluded'], currency.decimal_places)
                record.pricer_display_price = rounded_including if currency.compare_amounts(res['total_included'], price) else rounded_excluding

    def _get_create_or_update_body(self):
        """
        If the product related to a pricer tag needs to be updated:
         - we need to add its data to the JSON body used in create/update request
        """
        return {
            "itemId": str(self.id),
            "itemName": self.name,
            "price": self.pricer_display_price,
            "presentation": "NORMAL", # template name used on pricer tags
            "properties": {
                "currency": self.currency_id.symbol,
                "barcode": self.barcode or ""
            }
        }

    def write(self, vals):
        """
        Called whenever we update a product variant and click "save"
        If Pricer related fields are changed,
        We need to send the new information to Pricer API to display it
        """
        if any(val in PRICER_RELATED_FIELDS for val in vals):
            vals['pricer_product_to_create_or_update'] = True

        result = super().write(vals)
        if 'pricer_store_id' in vals:
            self.pricer_tag_ids.pricer_product_to_link = True

        return result
