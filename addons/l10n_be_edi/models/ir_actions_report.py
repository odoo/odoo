# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def postprocess_pdf_report(self, res_id, pdfreport_path, attachment_name):
        attachment_id = super(IrActionsReport, self).postprocess_pdf_report(res_id, pdfreport_path, attachment_name)
        country_id = self.env.user.company_id.country_id
        if attachment_id and self.model == 'account.invoice' and country_id == self.env.ref('base.be'):
            invoice_id = self.env[self.model].browse(res_id)
            if invoice_id.company_id.country_id == self.env.ref('base.be'):
                invoice_id.l10n_be_edi_generate_xml(attachment_id)
        return attachment_id
