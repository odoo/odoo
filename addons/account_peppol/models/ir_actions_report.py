from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _get_edi_document_format_codes_for_pdf_embedding(self):
        return super()._get_edi_document_format_codes_for_pdf_embedding() + ['peppol']
