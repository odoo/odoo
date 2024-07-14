# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def register_as_main_attachment(self, force=True):
        super().register_as_main_attachment(force=force)

        if self.res_model == 'hr.applicant':
            applicant = self.env['hr.applicant'].browse(self.res_id).exists()
            if applicant:
                applicant._autosend_for_digitization()
