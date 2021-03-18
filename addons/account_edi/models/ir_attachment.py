# -*- coding: utf-8 -*-
<<<<<<< HEAD
from odoo import models, fields, _
=======
from odoo import api, models, fields, _
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

<<<<<<< HEAD
    def unlink(self):
        # OVERRIDE
=======
    @api.ondelete(at_uninstall=False)
    def _unlink_except_government_document(self):
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
        linked_edi_documents = self.env['account.edi.document'].search([('attachment_id', 'in', self.ids)])
        linked_edi_formats_ws = linked_edi_documents.edi_format_id.filtered(lambda edi_format: edi_format._needs_web_services())
        if linked_edi_formats_ws:
            raise UserError(_("You can't unlink an attachment being an EDI document sent to the government."))
<<<<<<< HEAD
        return super().unlink()
=======
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
