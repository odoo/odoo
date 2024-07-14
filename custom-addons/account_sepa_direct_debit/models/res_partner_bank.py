# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_mandate(self):
        if self.env['sdd.mandate'].search([('partner_bank_id', 'in', self.ids),('state','=','active')]):
            raise UserError(_('You cannot delete a bank account linked to an active SEPA Direct Debit mandate.'))
