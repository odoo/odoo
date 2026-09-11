# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from datetime import date, timedelta

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    invoice_list = fields.One2many('account.move', 'partner_id',
                                   string="Invoice Details",
                                   readonly=True,
                                   domain=(
                                   [('payment_state', '=', 'not_paid'),
                                    ('move_type', '=', 'out_invoice')]))
    total_due = fields.Monetary(compute='_compute_for_followup', store=False,
                                readonly=True)
    next_reminder_date = fields.Date(compute='_compute_for_followup',
                                     store=False, readonly=True)
    total_overdue = fields.Monetary(compute='_compute_for_followup',
                                    store=False, readonly=True)
    followup_status = fields.Selection(
        [('in_need_of_action', 'In need of action'),
         ('with_overdue_invoices', 'With overdue invoices'),
         ('no_action_needed', 'No action needed')],
        string='Followup status',
        )

    def _compute_for_followup(self):
        """
        Compute the fields 'total_due', 'total_overdue' , 'next_reminder_date' and 'followup_status'
        """
        for record in self:
            total_due = 0
            total_overdue = 0
            today = fields.Date.today()
            for am in record.invoice_list:
                if am.company_id == self.env.company:
                    amount = am.amount_residual
                    total_due += amount

                    is_overdue = today > am.invoice_date_due if am.invoice_date_due else today > am.date
                    if is_overdue:
                        total_overdue += amount or 0
            min_date = record.get_min_date()
            action = record.action_after()
            if min_date:
                date_reminder = min_date + timedelta(days=action)
                if date_reminder:
                    record.next_reminder_date = date_reminder
            else:
                date_reminder = today
                record.next_reminder_date = date_reminder
            if total_overdue > 0 and date_reminder > today:
                followup_status = "with_overdue_invoices"
            elif total_due > 0 and date_reminder <= today:
                followup_status = "in_need_of_action"
            else:
                followup_status = "no_action_needed"
            record.total_due = total_due
            record.total_overdue = total_overdue
            record.followup_status = followup_status

    def get_min_date(self):
        today = date.today()
        for this in self:
            if this.invoice_list:
                min_list = this.invoice_list.mapped('invoice_date_due')
                while False in min_list:
                    min_list.remove(False)
                return min(min_list)
            else:
                return today

    def get_delay(self):
        delay = """select id,delay from followup_line where followup_id =
        (select id from account_followup where company_id = %s)
         order by delay limit 1"""
        self._cr.execute(delay, [self.env.company.id])
        record = self._cr.dictfetchall()

        return record


    def action_after(self):
        lines = self.env['followup.line'].search([(
            'followup_id.company_id', '=', self.env.company.id)])

        if lines:
            record = self.get_delay()
            for i in record:
                return i['delay']
