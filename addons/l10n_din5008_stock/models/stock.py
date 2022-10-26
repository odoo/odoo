from odoo import models, fields, _
from odoo.tools import format_date


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_din5008_addresses = fields.Binary(compute='_compute_l10n_din5008_addresses')

    def _compute_l10n_din5008_addresses(self):
        for record in self:
            record.l10n_din5008_addresses = data = []
            if record.partner_id:
                if record.picking_type_id.code == 'incoming':
                    data.append((_('Vendor Address:'), record.partner_id))
                if record.picking_type_id.code == 'internal':
                    data.append((_('Warehouse Address:'), record.partner_id))
                if record.picking_type_id.code == 'outgoing' and record.move_ids_without_package and record.move_ids_without_package[0].partner_id \
                        and record.move_ids_without_package[0].partner_id.id != record.partner_id.id:
                    data.append((_('Customer Address:'), record.partner_id))
