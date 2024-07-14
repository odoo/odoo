# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_approved_approval_request(self):
        """
            Prevent attachment deletion for an approval request
            that is in the approved, refused or cancel state.
        """
        approval_request_ids = [attachment.res_id for attachment in self if attachment.res_model == 'approval.request' and not attachment.res_field]
        if not approval_request_ids:
            return
        approval_requests = self.env['approval.request'].browse(approval_request_ids)
        for approval_request in approval_requests:
            if approval_request.request_status in ['approved', 'refused', 'cancel']:
                raise UserError(_("You cannot unlink an attachment which is linked to a validated, refused or cancelled approval request."))
