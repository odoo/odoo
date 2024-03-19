# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.http import request


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _inherit = ['approval.request']

    duration = fields.Integer(help='Approval duration in days', store=True)
    is_late = fields.Boolean()
    end_date = fields.Datetime()



    def action_get_my_records(self):
        domain = []
        domain = [('request_owner_id', '=', self.env.uid)]
        action = {
            'name': "My Requests",
            'view_mode': 'tree,form',
            'domain': domain,
            'res_model': 'approval.request',
            'type': 'ir.actions.act_window'
        }

        return action

    @api.depends('end_date', 'create_date')
    def _compute_duration(self):
        for rec in self:
            if rec.create_date and rec.end_date:
                rec.duration = (rec.end_date - rec.create_date).days
            else:
                rec.duration = 0

    # @api.onchange('employee_id')
    # def add_approval_manager(self):
    #     if self.approval_type == 'purchase' and self.approver_ids:
    #         self.update({
    #     'approver_ids': [
    #         (0, 0, {
    #             'user_id': self.request_owner_id.employee_id.parent_id.user_id.id,
    #             'required': True,
    #         })
    #     ]
    # })


class BaseApprovalRequest(models.AbstractModel):
    _name = "approval_base.base_approval_request"

    duration = fields.Integer(help='Approval duration in days', store=True)
    is_late = fields.Boolean()

    def compute_duration(self, approval_date, res_config_name):
        if self.create_date and approval_date:
            self.duration = (approval_date - self.create_date).days
            expected_duration = self.env['ir.config_parameter'].sudo().get_param(res_config_name)
            if expected_duration:
                if self.duration <= eval(expected_duration):
                    self.is_late = False
                else:
                    self.is_late = True
        else:
            self.duration = 0
