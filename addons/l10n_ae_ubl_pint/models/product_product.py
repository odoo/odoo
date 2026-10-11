from odoo import fields, models

# AE-GoodsType code list, exported as cbc:NatureCode ("Type of goods or services").
# https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/codelist/GoodsType/
L10N_AE_GOODS_SERVICE_TYPE_SELECTION = [
    ('DL8.48.8.2', 'Electronic Devices'),
    ('DL8.48.8.1', 'Gold and Diamonds'),
    ('DL8.48.3.1', 'Crude or refined oil'),
    ('DL8.48.3.2', 'Unprocessed or processed natural gas'),
    ('DL8.48.3.3', 'Pure hydrocarbons'),
]


class ProductProduct(models.Model):
    _inherit = ['product.product', 'l10n.ae.pint.check.mixin']

    # Item type (BTAE-13, cbc:CommodityCode) is one of G / S / B - this flag selects 'B',
    # the rest is derived from product.type in the exporter.
    # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-13/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/codelist/ItemType/
    l10n_ae_is_good_and_service = fields.Boolean(
        string='Is Good and Service',
        copy=False,
    )
    l10n_ae_goods_service_type = fields.Selection(
        string='Goods and Service Type',
        selection=L10N_AE_GOODS_SERVICE_TYPE_SELECTION,
        copy=False,
    )
    # BTAE-13's Item classification identifier (IBT-158, HS code) for Goods and Service
    # accounting code (BTAE-17, SAC) for Services are two different UBL nodes, but Odoo has no
    # own concept of either - one field covers both, the view picks the right label per product
    # type/l10n_ae_is_good_and_service.
    # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibt-158/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-17/
    l10n_ae_classification_code = fields.Char(
        string='HS / Service Accounting Code',
        copy=False,
    )

    def _l10n_ae_pint_group_by_error_code(self):
        self.ensure_one()
        # ibr-184-ae/ibr-185-ae/ibr-186-ae: Item classification identifier (Goods) and/or Service
        # accounting code (Services) MUST be provided, whichever the item type requires.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-184-ae/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-185-ae/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-186-ae/
        if not self.l10n_ae_classification_code:
            return (
                ("message", self.env._("Product(s) should have their HS / Service Accounting Code set.")),
                ("error_code", "l10n_ae_pint_product_classification_code_missing"),
                ("level", "danger"),
            )
        return False

    def _l10n_ae_pint_action_text(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.env._("View Product(s)")
