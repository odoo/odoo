# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def register_as_main_attachment(self, force=True):
        """Add the automatic scanning of attachments when registered as main.
           To avoid double scanning after message_post, we check that the automatic scanning is only made the first time.
        """
        self.ensure_one()
        super(IrAttachment, self).register_as_main_attachment(force=force)

        if self.res_model == 'hr.expense':
            related_record = self.env[self.res_model].browse(self.res_id)
            if not related_record.sample:
                related_record._autosend_for_digitization()
