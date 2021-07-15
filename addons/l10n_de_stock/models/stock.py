from odoo import models, fields, api, _
from odoo.tools import format_date


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    l10n_de_template_data = fields.Binary(compute='_compute_l10n_de_template_data')

    def _compute_l10n_de_template_data(self):
        for record in self:
            record.l10n_de_template_data = data = []
            if record.date:
                data.append((_("Date"), format_date(self.env, record.date)))
