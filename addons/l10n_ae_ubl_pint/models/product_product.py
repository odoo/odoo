from odoo import fields, models

L10N_AE_GOODS_SERVICE_TYPE_SELECTION = [
    ('DL8.48.8.2', 'Electronic Devices'),
    ('DL8.48.8.1', 'Gold and Diamonds'),
    ('DL8.48.3.1', 'Crude or refined oil'),
    ('DL8.48.3.2', 'Unprocessed or processed natural gas'),
    ('DL8.48.3.3', 'Pure hydrocarbons'),
]


class ProductProduct(models.Model):
    _inherit = 'product.product'

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
    l10n_ae_classification_code = fields.Char(
        string='HS / Service Accounting Code',
        copy=False,
    )

    def _group_by_error_code(self):
        self.ensure_one()
        # ibr-184-ae/ibr-185-ae/ibr-186-ae: Item classification identifier (Goods) and/or Service
        # accounting code (Services) MUST be provided, whichever the item type requires.
        if not self.l10n_ae_classification_code:
            return (
                ("message", self.env._("Product(s) should have their HS / Service Accounting Code set.")),
                ("error_code", "l10n_ae_ubl_pint_product_classification_code_missing"),
                ("level", "danger"),
            )
        return False

    def _l10n_ae_ubl_pint_export_check(self):
        """Validate Product for PINT AE compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update(
                {
                    temp_dict["error_code"]: {
                        "message": temp_dict["message"],
                        "level": temp_dict["level"],
                        "action": invalid_records._get_records_action(),
                        "action_text": self.env._("View Product(s)"),
                    },
                },
            )
        return alert_vals
