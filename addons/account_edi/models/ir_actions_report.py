# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        # OVERRIDE to embed some EDI documents inside the PDF.
        if self.model == 'account.move' and res_ids and len(res_ids) == 1 and pdf_content:
            invoice = self.env['account.move'].browse(res_ids)
            if invoice.is_sale_document() and invoice.state != 'draft':
                pdf_content = invoice.journal_id.edi_format_ids._embed_edis_to_pdf(pdf_content, invoice)

        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)
