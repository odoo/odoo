# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_l10n_cn_edi_fapiao_xml(self):
        if self.env['l10n_cn_edi.document'].sudo().search_count([('xml_id', 'in', self.ids)], limit=1):
            raise UserError(self.env._("You can't delete the XML of a fapiao: it's the record the tax bureau issued."))
