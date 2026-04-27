from odoo import api, models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_government_document(self):
        '''
        Prevents unlinking of xml attachments that are related to stock.picking records
        that have been sent to the government as delivery guides.
        '''
        if (
            (picking_attachments := self.filtered(
                lambda att: att.res_model == 'stock.picking' and att.mimetype == 'application/xml'
            )) and self.env['stock.picking'].search_count([
                ('id', 'in', picking_attachments.mapped('res_id')), ('l10n_ec_edi_status', '=', 'sent')
            ])
        ):
            raise UserError(_("You can't unlink an attachment being an EDI document sent to the government."))
