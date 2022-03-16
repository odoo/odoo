# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_government_document(self):
        linked_edi_flows = self.env['edi.flow'].search([('edi_file_ids.attachment_id', 'in', self.ids)])
        linked_edi_formats_ws = linked_edi_flows.filtered(lambda f: f._get_edi_format_settings().get('needs_web_services')).edi_format_id
        if linked_edi_formats_ws:
            raise UserError(_("You can't unlink an attachment being an EDI document sent to the government."))
