# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    l10n_es_asset_type = fields.Selection(
        selection=[
            ('11', 'Land used exclusively as landfills'),
            ('12', 'Buildings and Constructions'),
            ('21', 'Machinery'),
            ('22', 'Transport Equipment'),
            ('23', 'Computers and Other IT Equipment'),
            ('24', 'Furniture'),
            ('25', 'Installations'),
            ('26', 'Ships and Aircraft'),
            ('27', 'Mussel Raft'),
            ('28', 'Tools and Utensils'),
            ('29', 'Other Tangible Fixed Assets'),
            ('31', 'Patents and Trademarks'),
            ('32', 'Leasehold Transfer Rights'),
            ('33', 'Software'),
            ('39', 'Other Intangible Fixed Assets'),
            ('41', 'Cattle, Pigs, Sheep and Goats'),
            ('42', 'Horses and Non-Citrus Fruit Trees'),
            ('43', 'Citrus Fruit Trees and Vineyards'),
            ('44', 'Olive Groves'),
            ('49', 'Other Livestock and Agricultural Assets'),
        ],
        string="Asset Type",
        help="Type of asset according to the official Spanish classification."
    )


class AccountAssetVariant(models.Model):
    _inherit = 'account.asset.variant'

    l10n_es_sale_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Transfer Invoice",
        readonly=True,
        copy=False,
        help="Sales invoice with which the asset was transferred.",
    )

    def set_to_close(self, invoice_line_ids, date=None, message=None):
        # Keep the sale invoice to fill the transfer invoice columns of the
        # investment goods book.
        self.l10n_es_sale_move_id = invoice_line_ids.move_id[:1]
        return super().set_to_close(invoice_line_ids, date=date, message=message)
