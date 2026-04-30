from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _l10n_ae_pint_get_item_type(self):
        """ Item type (BTAE-13): 'B' for both, 'S' for a service, 'G' otherwise.

        None without an HS or SAC code (a discount, a down payment, ...), which BTAE-13 (0..1) allows.
        """
        self.ensure_one()
        if self.l10n_ae_is_good_and_service:
            return 'B'
        if not (self.l10n_ae_hs_code or self.l10n_ae_service_accounting_code):
            return False
        return 'S' if self.type == 'service' else 'G'

    def _l10n_ae_pint_get_item_values(self):
        """ Values of the account.move.line PINT AE item fields for a line of this product. """
        self.ensure_one()
        return {
            'l10n_ae_item_type': self._l10n_ae_pint_get_item_type(),
            'l10n_ae_goods_service_type': self.l10n_ae_goods_service_type,
            'l10n_ae_hs_code': self.l10n_ae_hs_code,
            'l10n_ae_service_accounting_code': self.l10n_ae_service_accounting_code,
        }
