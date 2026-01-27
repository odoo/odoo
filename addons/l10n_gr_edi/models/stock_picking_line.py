from odoo import models, fields
from odoo.addons.l10n_gr_edi.models.preferred_classification import (
    MEASUREMENT_UNIT_SELECTION,
)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    l10n_gr_edi_measurement_unit = fields.Selection(
        selection=MEASUREMENT_UNIT_SELECTION,
        string="myDATA Unit of Measure",
        compute='_compute_l10n_gr_edi_measurement_unit',
    )

    @api.depends('uom_id')
    def _compute_l10n_gr_edi_measurement_unit(self):
        uom_map = {name: code for code, name in MEASUREMENT_UNIT_SELECTION}
        for move in self:
            if move.company_id.account_fiscal_country_id.code == 'GR' and move.uom_id:
                move.l10n_gr_edi_measurement_unit = uom_map.get(move.uom_id.with_context(lang='en_US').name)
            else:
                move.l10n_gr_edi_measurement_unit = False
