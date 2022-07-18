# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    @api.model
    def default_get(self, fields):
        res = super(AccountInvoiceSend, self).default_get(fields)
        edi_state = self.env['account.move'].browse(res['invoice_ids']).mapped('edi_state')
        if any(state in edi_state for state in ['to_send', 'to_cancel']):
            if len(res['invoice_ids']) == 1:
                raise UserError("You can send and/or print an invoice which hasn't be validate by the EDI")
            ids_to_remove = self.env['account.move'].search([('id', 'in', res['invoice_ids']), '|', ('edi_state', '=', 'to_send'), ('edi_state', '=', 'to_cancel')]).mapped('id')
            res['invoice_ids'] = list(set(res['invoice_ids']) - set(ids_to_remove))

            # return {
            #     'warning':
            #         {'title': 'Warning',
            #         'message': ("Some invoices couldn't be send due to their EDI status"),
            #         }
            #     }
        return res

    def _return_confirmation_popup(self):
        view_id = self.env.ref('account_edi.view_mass_mail_confirm').id
        new_wizard = self.env['mass.mail.confirm'].create({})
        return {
                'type': 'ir.actions.act_window',
                'name': _('Confirm'),
                'view_mode': 'form',
                'view_type' : 'form',
                'view_id' : self.env.ref('account_edi.view_mass_mail_confirm'),
                'res_model': 'mass.mail.confirm',
                'res_id' : new_wizard.id,
                'target': 'current',
            }
