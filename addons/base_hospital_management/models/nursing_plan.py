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
from odoo import fields, models


class NursingPlan(models.Model):
    """Class holding nursing plan"""
    _name = 'nursing.plan'
    _description = "Nursing Plan"

    admission_id = fields.Many2one('hospital.inpatient',
                                   string='Patient',
                                   help='Name of the inpatient')
    date = fields.Datetime(string='Visit Time', help='Date and time of visit')
    status = fields.Char(string='Status',
                         help='Physical condition of the patient')
    notes = fields.Text(string='Note', help='You can add the notes here')
