# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SnailmailConfirmInvoiceSend(models.TransientModel):
    _name = 'snailmail.confirm.invoice'
    _description = 'Snailmail Confirm Invoice'

    invoice_send_id = fields.Many2one('account.invoice.send')

    def action_open(self):
        view = self.env.ref('snailmail_account.snailmail_confirm_invoice_view_form')
        return {
            'name': _('Snailmail'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }

    def action_confirm(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param('snailmail.confirm.invoice.warning_shown', True)
        return self.invoice_send_id._print_action()

    def action_cancel(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param('snailmail.confirm.invoice.warning_shown', True)
        return self.invoice_send_id.send_and_print_action()

    @api.model
    def show_warning(self):
        return not self.env['ir.config_parameter'].sudo().get_param('snailmail.confirm.invoice.warning_shown', False)
