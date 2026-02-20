# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nHuEdiReceiveBillsWizard(models.TransientModel):
    _name = 'l10n_hu_edi.receive.bills.wizard'
    _description = "Receive Bills Wizard"

    l10n_hu_edi_receive_from = fields.Datetime(default=lambda self: min(self.env.companies.mapped('l10n_hu_edi_last_nav_sync')) or fields.Datetime.now() - timedelta(weeks=1))
    l10n_hu_edi_receive_to = fields.Datetime(default=lambda self: fields.Datetime.now())

    def action_receive_bills(self):
        self.ensure_one()

        if (self.l10n_hu_edi_receive_to - self.l10n_hu_edi_receive_from) > timedelta(days=35):
            raise UserError(_("The length of the interval specified by the query parameter can be up to 35 days."))

        companies_sudo = self.env.companies.filtered_domain([('l10n_hu_edi_server_mode', 'in', ['test', 'production'])]).sudo()
        companies_sudo.l10n_hu_edi_receive_from = self.l10n_hu_edi_receive_from
        companies_sudo.l10n_hu_edi_receive_to = self.l10n_hu_edi_receive_to
        self.env.ref('l10n_hu_edi_receive.ir_cron_receive_inbound_invoices_wizard')._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': _("Receiving bills"),
                'message': _("Bills are being received in the background."),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
