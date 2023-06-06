from odoo import _, models
from odoo.exceptions import UserError

class ReSequenceWizard(models.TransientModel):
    _inherit = 'account.resequence.wizard'
    
    def resequence(self):
        edi_is_send = self.move_ids.edi_document_ids.filtered(lambda d: d.edi_format_id._needs_web_services() and d.state in ('sent'))
        if edi_is_send:
            move_types_name = " and ".join(set(edi_is_send.move_id.mapped('type_name')))
            service_types_name = " and ".join(set(edi_is_send.edi_format_id.mapped('name')))
            raise UserError(_(
                "Some %s has already sent to %s, so you can't change sequence.\n"\
                "You can cancel it and create %s with new sequeace.", move_types_name, service_types_name, move_types_name))
        super().resequence()
