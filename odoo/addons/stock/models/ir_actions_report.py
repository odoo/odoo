from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        if report.report_name == 'stock.report_reception_report_label' and not docids:
            docids = data['docids']
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'docs': docs,
            })
        return data
