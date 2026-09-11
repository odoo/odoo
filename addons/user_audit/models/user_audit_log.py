# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import api, fields, models


class UserAuditLogs(models.Model):
    """ For tracking user activity by adding user logs """
    _name = "user.audit.log"
    _description = "User Audit Details"

    name = fields.Char(string="Reference", required=True, readonly=True,
                       default='New', help="For getting reference")
    user_id = fields.Many2one('res.users', string="User",
                              help="For getting user")
    record = fields.Integer(string="Record ID",
                            help="For getting which record has accessed")
    model_id = fields.Many2one('ir.model', string="Object",
                               help="For getting which model has accessed")
    operation_type = fields.Selection(selection=[('read', 'Read'),
                                                 ('write', 'Write'),
                                                 ('create', 'Create'),
                                                 ('delete', 'Delete')],
                                      string="Type",
                                      help="For getting which operation has been performed")
    date = fields.Datetime(string="Date",
                           help="For getting which time the operation has done")

    @api.model_create_multi
    def create(self, values):
        """ For adding sequence number """
        vals = values[0]
        if vals.get('name', 'New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'user.audit.log')
        res = super(UserAuditLogs, self).create(vals)
        return res
