from odoo import models, fields, _
from odoo.tools import format_date


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_de_template_data = fields.Binary(compute='_compute_l10n_de_template_data')

    def _compute_l10n_de_template_data(self):
        for record in self:
            record.l10n_de_template_data = data = []
            if record.origin:
                data.append((_("Order"), record.origin))
            if record.state == 'done':
                data.append((_("Shipping Date"), format_date(self.env, record.date_done)))
            else:
                data.append((_("Shipping Date"), format_date(self.env, record.scheduled_date)))
