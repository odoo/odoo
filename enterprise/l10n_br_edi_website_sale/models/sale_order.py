# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def set_delivery_line(self, carrier, amount):
        """Override. Copy over the default transporter and freight model from the delivery carrier configuration."""
        res = super().set_delivery_line(carrier, amount)
        for order in self:
            order.l10n_br_edi_transporter_id = carrier.l10n_br_edi_transporter_id
            order.l10n_br_edi_freight_model = carrier.l10n_br_edi_freight_model
        return res
