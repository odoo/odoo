# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions  (odoo@cybrosys.com)
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
################################################################################
from odoo import api, fields, models


class PatientBooking(models.Model):
    """Class holding patient booking"""
    _name = 'patient.booking'
    _inherit = 'mail.thread'
    _description = 'Patient Booking'
    _rec_name = 'patient_id'

    booking_reference = fields.Char(string="OP Number",
                                    help='Reference number indicating '
                                         'the booking', readonly=True,
                                    default='New')
    patient_id = fields.Many2one('res.partner', string='Patient',
                                 domain=[('patient_seq', 'not in',
                                          ['New', 'Employee', 'User'])],
                                 help='Choose the patient for booking',
                                 required=True)
    doctor_id = fields.Many2one('doctor.allocation',
                                string='Doctor',
                                help='Select the doctor',
                                required=True,
                                domain=[('slot_remaining', '>', 0),
                                        ('date', '=', fields.date.today()),
                                        ('state', '=', 'confirm')])
    currency_id = fields.Many2one('res.currency',
                                  string='Currency',
                                  help='Currency in which consultation fee '
                                       'is calculating',
                                  default=lambda self: self.env.user.company_id
                                  .currency_id.id,
                                  required=True)
    consultation_fee = fields.Monetary(
        related='doctor_id.doctor_id.consultancy_charge', string="Fee",
        help='Consultation fee',
        readonly=True)
    booking_date = fields.Date(string="Booking Date", help='Date of booking',
                               default=fields.Date.today())
    reason = fields.Text(string='Reason', help='Reason for booking')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirmed'),
         ('cancel', 'Cancelled')],
        default='draft', string='State', help='State of patient booking')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)
    slot = fields.Float(string='Slot', help='Slot for the patient',
                        copy=False)

    @api.model
    def create(self, vals):
        """Method for creating booking reference"""
        if vals.get('booking_reference', 'New') == 'New':
            vals['booking_reference'] = self.env['ir.sequence'].next_by_code(
                'patient.booking') or 'New'
        return super().create(vals)

    @api.onchange('booking_date')
    def _onchange_booking_date(self):
        """Method for adding domain for doctor_id"""
        return {'domain': {'doctor_id': [('slot_remaining', '>', 0),
                                         ('date', '=', self.booking_date),
                                         ('state', '=', 'confirm')]}}

    def action_confirm_booking(self):
        """Confirmation of booking"""
        if self.doctor_id.latest_slot == 0:
            self.slot = self.doctor_id.work_from
        else:
            self.slot = self.doctor_id.latest_slot + self.doctor_id.time_avg
        self.doctor_id.latest_slot = self.slot
        self.state = 'confirm'

    def action_booking_cancel(self):
        """Method for cancelling a booking"""
        self.state = 'cancel'
