# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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


class BloodBank(models.Model):
    """Class holding Blood bank details"""
    _name = 'blood.bank'
    _description = "Blood Bank"

    partner_id = fields.Many2one('res.partner',
                                 string='Donor Name',
                                 domain=[('patient_seq', 'not in',
                                          ['New', 'Employee', 'User'])],
                                 help='Name of the blood donor',
                                 required=True)
    name = fields.Char(string='Sequence',
                       help='Sequence number indicating the blood bank',
                       index=True,
                       default=lambda self: 'New')
    date = fields.Date(string='Date', help='Blood donating date',
                       default=fields.date.today())
    blood_type = fields.Selection([('a_positive', 'A+'),
                                   ('a_negative', 'A-'),
                                   ('b_positive', 'B+'), ('b_negative', 'B-'),
                                   ('o_positive', 'O+'), ('o_negative', '0-'),
                                   ('ab_positive', 'AB+'),
                                   ('ab_negative', 'AB-')],
                                  string='Blood Group',
                                  help='Choose your blood group', required=True,
                                  group_expand='_group_expand_states')
    blood_donation_ids = fields.One2many('blood.donation',
                                         'blood_bank_id',
                                         string='Contra Indications',
                                         help='Lists all the '
                                              'contraindications')
    state = fields.Selection([('avail', 'Available'),
                              ('not', 'Unavailable')],
                             string='State', help='State of the blood donation',
                             readonly=True, default="avail")
    assigned_patient_id = fields.Many2one('res.partner',
                                          string='Receiver',
                                          domain=[('patient_seq', 'not in',
                                                   ['New', 'Employee',
                                                    'User'])],
                                          help='Choose the patient to whom '
                                               'blood is donating')

    @api.model
    def create(self, vals):
        """Function for creating blood sequence number"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'blood.bank') or 'New'
        return super().create(vals)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Function for listing all contra indications"""
        self.blood_donation_ids = False
        self.sudo().write({
            'blood_donation_ids': [(0, 0, {
                'questions': rec.blood_donation_question})
                                   for rec in
                                   self.env['contra.indication'].sudo().search(
                                       [])]})

    def _group_expand_states(self, states, domain, order):
        """Method for expanding all blood groups in kanban view"""
        return [key for
                key, val in type(self).blood_type.selection]

    def action_blood_available(self):
        """Change the state to unavailable"""
        self.sudo().write({
            'state': 'not'
        })

    def action_change_availability(self):
        """Cron action for changing the state of the record"""
        for rec in self.sudo().search([]):
            if rec.date <= fields.Date.subtract(fields.Date.today(), months=1):
                rec.state = 'avail'
