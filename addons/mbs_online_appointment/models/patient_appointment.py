# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date


# from twilio.rest import Client
# from twilio.base.exceptions import TwilioRestException


class PatientAppointment(models.Model):
    _name = 'patient.appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'patient online appointment'

    appoi_sequence = fields.Char(string="Appointment", readonly="True")
    name = fields.Char(string="Patient")
    date_of_birth = fields.Date(string="Date Of Birth", tracking=True)
    date = fields.Date(string="Appointment Date", default=lambda self: date.today())
    time = fields.Selection([
        ('10:00', '10:00 AM'), ('10:30', '10:30 AM'),
        ('11:00', '11:00 AM'), ('11:30', '11:30 AM'),
        ('12:00', '12:00 PM'), ('12:30', '12:30 PM'),
        ('03:00', '03:00 PM'), ('03:30', '03:30 PM'),
        ('04:00', '04:00 PM'), ('04:30', '04:30 PM'),
        ('05:00', '05:00 PM'), ('05:30', '05:30 PM'),
    ], string="Time", tracking=True)
    age = fields.Integer(string="Age", compute='_compute_age', readonly=True, store=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')], string="Gender",
                              tracking=True)

    city = fields.Char('City')
    hospital = fields.Many2one("confi.hospital", string="Hospital")
    mobile = fields.Char(unaccent=False)
    blood_id = fields.Many2one(comodel_name="blood.group", string='Blood Group')
    dieases = fields.Many2one("dieases.dieases", string="Dieases/Reason")
    dr_nm = fields.Many2one('doctor.config', string="Doctor")

    @api.depends('date_of_birth')
    def _compute_age(self):
        for record in self:
            if record.date_of_birth and record.date_of_birth <= fields.Date.today():
                record.age = relativedelta(
                    fields.Date.from_string(fields.Date.today()),
                    fields.Date.from_string(record.date_of_birth)).years
            else:
                record.age = 0

    def send_message(self, mobile_number, message):
        print('send Message')
        # account_sid = self.env["ir.config_parameter"].get_param("mbs_online_appointment.account_sid")
        # auth_token = self.env["ir.config_parameter"].get_param("mbs_online_appointment.auth_token")
        # twilio_number = self.env["ir.config_parameter"].get_param("mbs_online_appointment.twilio_number")
        #
        # try:
        #     client = Client(account_sid, auth_token)
        #     message = client.messages.create(
        #         body=message,
        #         from_=twilio_number,
        #         to=mobile_number
        #     )
        #     print("Message sent successfully:", message.sid)
        # except TwilioRestException as e:
        #     print("Error sending message:", e)

    @api.model
    def create(self, vals):
        vals['appoi_sequence'] = self.env['ir.sequence'].next_by_code('patient.appointment')
        rec = super(PatientAppointment, self).create(vals)

        # Send SMS notification
        if rec.mobile:
            message = f"Hi {rec.name}, your appointment is booked on {rec.date}. Thank you."
            rec.send_message(rec.mobile, message)
        return rec
