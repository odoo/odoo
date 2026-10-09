# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: odoo@cybrosys.com
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
#############################################################################
from odoo import models, fields


class VisitorDetails(models.Model):
    _name = 'fo.visitor'
    _description = 'Visitor Details'

    name = fields.Char(string="Visitor", required=True)
    visitor_image = fields.Binary(string='Image', attachment=True)
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street2")
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State',
                               ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country',
                                 ondelete='restrict')
    phone = fields.Char(string="Phone", required=True)
    email = fields.Char(string="Email", required=True)
    id_proof = fields.Many2one('id.proof', string="ID Proof")
    id_proof_no = fields.Char(string="ID Number", help='Id proof number')
    company_info = fields.Many2one('res.partner', string="Company",
                                   help='Visiting persons company details')
    visit_count = fields.Integer(compute='_no_visit_count', string='# Visits')

    _sql_constraints = [
        ('field_uniq_email_and_id_proof', 'unique (email,id_proof)',
         "Please give the correct data !"),
    ]

    def _no_visit_count(self):
        data = self.env['fo.visit'].search(
            [('visitor', 'in', self.ids), ('state', '!=', 'cancel')]).ids
        self.visit_count = len(data)


class VisitorProof(models.Model):
    _name = 'id.proof'
    _rec_name = 'id_proof'
    _description = 'Visitor Proof'

    id_proof = fields.Char(string="Name")
    code = fields.Char(string="Code")
