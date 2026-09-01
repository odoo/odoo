# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import format_date


class LotLabelLayout(models.TransientModel):
    _inherit = 'lot.label.layout'

    def _prepare_lot_gs1_barcode_extra_data(self, lot):
        barcode = super()._prepare_lot_gs1_barcode_extra_data(lot)
        if lot.use_expiration_date:
            if lot.use_date:
                barcode += f"15{lot.use_date.strftime('%y%m%d')}"
            if lot.expiration_date:
                barcode += f"17{lot.expiration_date.strftime('%y%m%d')}"
        return barcode

    def _prepare_label_values(self, lot, copies):
        label = super()._prepare_label_values(lot, copies)
        if lot.use_expiration_date:
            label.update({
                'use_date': format_date(self.env, lot.use_date),
                'expiration_date': format_date(self.env, lot.expiration_date),
            })
        return label
