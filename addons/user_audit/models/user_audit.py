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


class UserAudit(models.Model):
    """We can manage user audit configuration.We can add user
                model etc. which are to track"""
    _name = "user.audit"
    _description = "User Audit Log Configuration"

    name = fields.Char(required=True, string="Name", help="Name of the log")
    is_read = fields.Boolean(string="Read",
                             help="Enabling we can track all read activities "
                                  "It will track all your read activity that "
                                  "may increase the size of the log that may "
                                  "cause some problem with your data base")
    is_write = fields.Boolean(string="Write",
                              help="Enabling we can track all write activities")
    is_create = fields.Boolean(string="Create",
                               help="Enabling we can track all create activities")
    is_delete = fields.Boolean(string="Delete",
                               help="Enabling we can track all delete activities")
    is_all_users = fields.Boolean(string="All Users",
                                  help="Enabling we can track activities of all users")
    user_ids = fields.Many2many('res.users', string="Users",
                                help="Manage users")
    model_ids = fields.Many2many('ir.model', string="Model",
                                 help='Used to select which model is to track')

    @api.model
    def create_audit_log_for_create(self, res_model):
        """ Used to create user audit log based on the create operation """
        model_id = self.env['ir.model'].search([('model', '=', res_model)]).id
        audit = self.search([('model_ids', 'in', model_id)])
        if audit and audit.is_create:
            self.env['user.audit.log'].create({
                'user_id': self.env.user.id,
                'model_id': model_id,
                'operation_type': 'create',
                'date': fields.Datetime.now()
            })
        return res_model

    @api.model
    def create_audit_log_for_read(self, res_model, record_id):
        """ Used to create user audit log based on the read operation """
        model_id = self.env['ir.model'].search([('model', '=', res_model)]).id
        audit = self.search([('model_ids', 'in', model_id)])
        if audit and audit.is_read:
            self.env['user.audit.log'].create({
                'user_id': self.env.user.id,
                'model_id': model_id,
                'record': record_id,
                'operation_type': 'read',
                'date': fields.Datetime.now()
            })
        return res_model

    @api.model
    def create_audit_log_for_delete(self, res_model, record_id):
        """ Used to create user audit log based on the delete operation """
        model = self.env['ir.model'].search([('model', '=', res_model)])
        model_id = self.env[res_model].browse(record_id)
        audit = self.search([('model_ids', 'in', model.id)])
        if audit and audit.is_delete and record_id and model_id:
            self.env['user.audit.log'].create({
                'user_id': self.env.user.id,
                'model_id': model.id,
                'record': record_id,
                'operation_type': 'delete',
                'date': fields.Datetime.now()
            })
        return res_model

    @api.model
    def create_audit_log_for_write(self, res_model, record_id):
        """ Used to create user audit log based on the write operation """
        model_id = self.env['ir.model'].search([('model', '=', res_model)]).id
        audit = self.search([('model_ids', 'in', model_id)])
        if audit and audit.is_write:
            self.env['user.audit.log'].create({
                'user_id': self.env.user.id,
                'model_id': model_id,
                'record': record_id,
                'operation_type': 'write',
                'date': fields.Datetime.now()
            })
        return res_model
