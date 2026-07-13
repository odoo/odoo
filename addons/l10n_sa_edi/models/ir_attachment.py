from odoo import api, models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_rejected_zatca_document(self):
        '''
        Prevents unlinking of rejected XML documents
        '''
        descr = 'Rejected ZATCA Document not to be deleted - ثيقة ZATCA المرفوضة لا يجوز حذفها'
        for attach in self.filtered(lambda a: a.description == descr and a.res_model == 'account.move'):
            move = self.env['account.move'].browse(attach.res_id)
            if move.country_code == "SA":
                raise UserError(_("You can't unlink an attachment being an EDI document refused by the government."))
