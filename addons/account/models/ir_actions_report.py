# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.multi
    def retrieve_attachment(self, record):
        # get the original invoice through the message_main_attachment_id field of the record
        if self.report_name == 'account.report_original_vendor_bill':
            if record.message_main_attachment_id.mimetype == 'application/pdf':
                return record.message_main_attachment_id
            else:
                return False
        else:
            return super(IrActionsReport, self).retrieve_attachment(record)

    @api.multi
    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        # don't include the generated dummy report
        if self.report_name == 'account.report_original_vendor_bill':
            pdf_content = None
            res_ids = None
        if not save_in_attachment:
            raise UserError(_("No original vendor bills could be found for any of the selected vendor bills."))
        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)