# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Amaya Aravind EV (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from datetime import timedelta
from odoo import fields, models


class AccountMove(models.Model):
    """Class for the inherited model account. move"""
    _inherit = 'account.move'

    def action_send_mail_invoice(self):
        """Function for sending mail by checking date in settings. """
        values = self.env['res.config.settings'].default_get(
            list(self.env['res.config.settings'].fields_get()))
        if values['reminder_invoicing'] is not False:
            for record in self.search([]):
                if record.invoice_date_due and record.move_type == 'out_invoice':
                    if record.state == 'draft':
                        if record.invoice_date_due == timedelta(int(values[
                                                                        'set_date_invoicing'])) + fields.Date.today():
                            mail_template = self.env.ref(
                                'sale_invoice_due_date_reminder.invoice_due_mail_template')
                            mail_template.send_mail(record.id, force_send=True)
                    elif record.state == 'posted' and record.payment_state != 'paid' and record.invoice_date_due == timedelta(
                            int(values[
                                    'set_date_invoicing'])) + fields.Date.today():
                        mail_template = self.env.ref(
                            'sale_invoice_due_date_reminder.invoice_due_mail_template')
                        mail_template.send_mail(record.id, force_send=True)
