# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError


class L10nHuEdiReceiveBillsWizard(models.TransientModel):
    _name = 'l10n_hu_edi_receive.bills.wizard'
    _description = "Receive Bills Wizard"

    l10n_hu_edi_receive_from = fields.Datetime(default=lambda self: fields.Datetime.now() - timedelta(weeks=1))
    l10n_hu_edi_receive_to = fields.Datetime(default=lambda self: fields.Datetime.now())

    def action_receive_bills(self):
        self.ensure_one()

        if (self.l10n_hu_edi_receive_to - self.l10n_hu_edi_receive_from) > timedelta(days=35):
            raise UserError(self.env._("The length of the interval specified by the query parameter can be up to 35 days."))

        moves = self.env['account.move']
        for company in self.env.companies.filtered(lambda c: c.l10n_hu_edi_server_mode in ('test', 'production')):
            moves += company.l10n_hu_edi_receive_inbound_invoices(self.l10n_hu_edi_receive_from, self.l10n_hu_edi_receive_to)

        if moves:
            message = self.env._("Bills were successfully received from NAV.")
            action = moves._get_records_action(
                name=self.env._("Bills received from NAV"),
                views=[(self.env.ref('account.view_in_invoice_bill_tree').id, 'list'), (False, 'form')] if len(moves) > 1 else [(False, 'form')],
            )
        else:
            message = self.env._("No bills received from NAV.")
            action = {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': message,
                'next': action,
            },
        }
