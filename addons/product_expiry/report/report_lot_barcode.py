from odoo import models


class ReportStockLotLabel(models.AbstractModel):
    _inherit = 'report.stock.report_lot_label'

    def _prepare_lot_label(self, lot):
        label = super()._prepare_lot_label(lot)
        if lot.use_expiration_date:
            label.update({
                'label_class': '',
                'use_date': lot.use_date,
                'expiration_date': lot.expiration_date,
            })
        return label
