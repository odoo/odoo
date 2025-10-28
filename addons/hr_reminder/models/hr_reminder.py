# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import models, fields


class HrReminder(models.Model):
    """Model for Employees Reminder"""
    _name = 'hr.reminder'
    _description = "HR Reminder"

    name = fields.Char(string='Title', required=True,
                       help="Title of the reminder")
    model_id = fields.Many2one('ir.model', help="Choose the model name",
                               string="Model", required=True,
                               ondelete='cascade',
                               domain="[('model', 'like','hr')]")
    field_id = fields.Many2one('ir.model.fields', string='Field',
                               help="Choose the field",
                               domain="[('model_id', '=',model_id),"
                                      "('ttype', 'in', ['datetime','date'])]"
                               , required=True, ondelete='cascade')
    search_by = fields.Selection([('today', 'Today'),
                                  ('set_period', 'Set Period'),
                                  ('set_date', 'Set Date'), ],
                                 required=True, string="Search By",
                                 help="Search by the given field")
    days_before = fields.Integer(string='Reminder before',
                                 help="Number of days before the reminder "
                                      "should show")
    date_set = fields.Date(string='Select Date',
                           help="Select the reminder set date")
    date_from = fields.Date(string="Start Date",
                            help="Start date to show the reminder")
    date_to = fields.Date(string="End Date",
                          help="End date to not show the reminder")
    expiry_date = fields.Date(string="Reminder Expiry Date",
                              help="Expiry date to expires out the reminder")
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, help="he company to which this reminder belongs.",
                                 default=lambda self: self.env.user.company_id)
