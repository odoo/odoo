from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _add_to_wave(self, wave=False):
        wave_id = super()._add_to_wave(wave=wave)
        wave_id.update({
            'dock_id': self.env.context.get('dock_id') if wave_id.dock_id else False,
            'vehicle_id': self.env.context.get('vehicle_id'),
            'vehicle_category_id': self.env.context.get('vehicle_category_id'),
        })

        return wave_id
