import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Tag id should be a 17 characters string composed of a letter followed by 16 digits
PRICER_TAG_ID_LENGTH = 17

class PricerTag(models.Model):
    _name = 'pricer.tag'
    _description = 'Pricer electronic tag'

    name = fields.Char(
        string='Pricer Tag Barcode ID',
        help='It is recommended to use a barcode scanner for input',
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Associated Product',
        required=True,
        ondelete='cascade',
    )
    pricer_store_id = fields.Many2one(
        comodel_name='pricer.store',
        string='Associated Pricer Store',
        required=True,
        ondelete='cascade',
        related='product_id.pricer_store_id',
    )

    # When we create a new pricer tag, it needs to be linked to its associated product
    pricer_product_to_link = fields.Boolean(default=True)

    # ------------------------- CONSTRAINS -------------------------

    # Avoid creating multiple Pricer tags with the same id
    _sql_constraints = [
        ('name_unique', 'unique (name)',
         "A Pricer tag with this barcode id already exists"),
    ]

    @api.constrains('name')
    def _check_tag_id(self):
        """
        Tag id should be a 17 characters string composed of a letter followed by 16 digits
        [LETTER][16 digits]

        Examples:
        N4081315787313278
        B4093233954716057
        A4073091573616030
        """
        for record in self:
            tag_id = record.name
            if len(tag_id) != PRICER_TAG_ID_LENGTH or not tag_id[0].isalpha() or not tag_id[1:].isdigit():
                raise ValidationError(_("Tag id should be a 17 characters string composed of a letter followed by 16 digits"))

    # ------------------------- ODOO METHODS -------------------------

    def write(self, vals):
        """
        If a product or associated to this tag has changed
        --> Link it to a new one
        """
        if 'product_id' in vals:
            vals['pricer_product_to_link'] = True
        return super().write(vals)

    # ------------------------- PRICER API METHODS -------------------------

    @api.ondelete(at_uninstall=True)
    def _unlink_product_on_delete(self):
        """
        When we delete a Pricer tag / unlink it from a product
        --> unlink it from the associated Pricer store
        --> stop displaying the linked product on it directly
        """
        for record in self:
            record.pricer_store_id.unlink_label(record.name)

    def _get_link_body(self):
        """
        Get the JSON related to a link request for this tag
        """
        return {
            "barcode": self.name,
            "links": [
                {
                    "barcode": self.name,
                    "itemId": self.product_id.id,
                }
            ]
        }
