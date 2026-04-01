from odoo import api, models


class ReportInvoiceWithoutPayment(models.AbstractModel):
    _name = 'report.account.report_invoice'
    _inherit = 'report.account.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)
        rslt['docs'] = rslt['docs'].with_context(partner_display_name_hide_company=True)
        return rslt
