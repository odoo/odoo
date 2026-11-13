from odoo import models


class ReportCmrBatch(models.AbstractModel):
    _name = 'report.stock_fleet.report_cmr_batch'
    _description = 'CMR Batch Report'

    def _get_report_values(self, docids, data=None):
        outgoing_batches = self.env['stock.picking.batch'].browse(docids).filtered(lambda b: b.picking_type_id.code == 'outgoing')
        kg_uom = self.env.ref('uom.product_uom_kgm')
        m3_uom = self.env.ref('uom.product_uom_cubic_meter')

        pickings_data = []
        has_carrier_id = 'carrier_id' in self.env['stock.picking']._fields
        pickings_groups = outgoing_batches.picking_ids.grouped(lambda p: (p.partner_id, p.carrier_id if has_carrier_id else False))

        for pickings_group in pickings_groups.values():
            pickings_data.append(self.env['report.stock_fleet.report_cmr']._get_pickings_data(pickings_group, kg_uom, m3_uom))

        return {
            'docs': outgoing_batches,
            'pickings_data': pickings_data,
            'kg_uom_id': kg_uom,
            'm3_uom_id': m3_uom,
        }
