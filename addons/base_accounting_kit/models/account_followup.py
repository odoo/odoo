# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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

from odoo import fields, models


class Followup(models.Model):
    _name = 'account.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'

    followup_line_ids = fields.One2many('followup.line', 'followup_id',
                                        'Follow-up', copy=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    name = fields.Char(related='company_id.name', readonly=True)


class FollowupLine(models.Model):
    _name = 'followup.line'
    _description = 'Follow-up Criteria'
    _order = 'delay'

    name = fields.Char('Follow-Up Action', required=True, translate=True)
    sequence = fields.Integer(
        help="Gives the sequence order when displaying a list of follow-up lines.")
    delay = fields.Integer('Due Days', required=True,
                           help="The number of days after the due date of the invoice"
                                " to wait before sending the reminder."
                                "  Could be negative if you want to send a polite alert beforehand.")
    followup_id = fields.Many2one('account.followup', 'Follow Ups',
                                  ondelete="cascade")
