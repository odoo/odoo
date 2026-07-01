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


class BloodDonation(models.Model):
    """Class holding blood donation details"""
    _name = 'blood.donation'
    _description = 'Blood Donation'
    _rec_name = 'questions'

    questions = fields.Text(string='Contra Indications',
                            help='Contraindications of the blood donor')
    is_true = fields.Boolean(string='Is True',
                             help='True for contraindications')
    blood_bank_id = fields.Many2one('blood.bank',
                                    string='Blood Bank',
                                    help='Blood bank corresponding to the '
                                         'donor')
