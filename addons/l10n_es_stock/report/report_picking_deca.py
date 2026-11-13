# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportDeca(models.AbstractModel):
    _name = 'report.l10n_es_stock.report_deca'
    _inherit = ['report.stock_fleet.report_cmr']
    _description = 'DeCA Report'

    def _get_report_values(self, docids, data=None):
        pickings = self.env['stock.picking'].browse(docids).filtered(lambda p: p.picking_type_id.code == 'outgoing')
        kg_uom = self.env.ref('uom.product_uom_kgm')
        m3_uom = self.env.ref('uom.product_uom_cubic_meter')

        def _get_destination_key(picking):
            consignee = picking.sale_id.partner_id if 'sale_id' in picking._fields and picking.sale_id else picking.partner_id
            return (picking.partner_id, consignee)

        pickings_by_destination = pickings.grouped(_get_destination_key)
        pickings_data = [
            self._get_pickings_data(destination_pickings, kg_uom, m3_uom)
            for destination_pickings in pickings_by_destination.values()
        ]

        return {
            'docs': pickings,
            'pickings_data': pickings_data,
            'kg_uom_id': kg_uom,
            'm3_uom_id': m3_uom,
        }
