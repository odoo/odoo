# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _should_generate_commercial_invoice(self):
        super(StockPicking, self)._should_generate_commercial_invoice()
        return True

    def _get_l10n_in_dropship_dest_partner(self):
        """
        To be overriden by `l10n_in_purchase_stock` will be ideal to use it for `l10n_in_ewaybill_stock`
        returns destination partner from purchase_id
        """
        pass

    def _l10n_in_get_invoice_partner(self):
        """
        To be overriden by `l10n_in_sale_stock` will be ideal to use it for `l10n_in_ewaybill_stock`
        returns invoice partner from sale_id
        """
        pass

    def _l10n_in_get_fiscal_position(self):
        """
        To be inherited by `l10n_in_*_stock` will be ideal to use it for `l10n_in_ewaybill_stock`
        returns fiscal position from order
        """
        pass
