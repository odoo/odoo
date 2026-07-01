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


class SaleOrder(models.Model):
    """Class for inherited model sale order."""
    _inherit = 'sale.order'

    due_date_order = fields.Date(string="Due Date",
                                 help='Set a due date for the Order')

    def action_send_mail_sale_order(self):
        """Function for sending mail by checking date in settings. """
        values = self.env['res.config.settings'].default_get(
            list(self.env['res.config.settings'].fields_get()))
        if values['reminder_sales'] is not False:
            for record in self.search([]):
                if record.due_date_order and record.invoice_status != 'invoiced':
                    if record.invoice_status == 'upselling' or record.invoice_status == 'to invoice':
                        if record.due_date_order == timedelta(int(values[
                                                                      'set_date_sales'])) + fields.Date.today():
                            mail_template = self.env.ref(
                                'sale_invoice_due_date_reminder.sale_order_due_mail_template')
                            mail_template.send_mail(record.id,
                                                    force_send=True)
                    elif record.invoice_status == 'no':
                        if record.invoice_count == 0:
                            if record.due_date_order == timedelta(
                                    int(values[
                                            'set_date_sales'])) + fields.Date.today():
                                mail_template = self.env.ref(
                                    'sale_invoice_due_date_reminder.sale_order_due_mail_template')
                                mail_template.send_mail(record.id,
                                                        force_send=True)
                        else:
                            payment_list = record.invoice_ids.mapped(
                                'payment_state')
                            if (
                                    'not_paid' or 'in_payment' or 'partial' or 'reversed' or 'invoicing_legacy') in payment_list:
                                if record.due_date_order == timedelta(
                                        int(values[
                                                'set_date_sales'])) + fields.Date.today():
                                    mail_template = self.env.ref(
                                        'sale_invoice_due_date_reminder.sale_order_due_mail_template')
                                    mail_template.send_mail(record.id,
                                                            force_send=True)
