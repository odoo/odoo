# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailActivityPlanTemplate(models.Model):
    _inherit = 'mail.activity.plan.template'

    sign_template_id = fields.Many2one('sign.template', string='Document to sign')
    employee_role_id = fields.Many2one(
        "sign.item.role", string="Employee Role",
        domain="[('id', 'in', sign_template_responsible_ids)]",
        compute="_compute_employee_role_id", readonly=False, store=True,
        help="Employee's role on the templates to sign. The same role must be present in all the templates")
    sign_template_responsible_ids = fields.Many2many('sign.item.role', compute='_compute_responsible_ids')
    responsible_count = fields.Integer(compute='_compute_responsible_ids')
    is_signature_request = fields.Boolean(compute='_compute_signature_request')

    @api.depends('activity_type_id')
    def _compute_signature_request(self):
        for template in self:
            template.is_signature_request = template.activity_type_id.category == 'sign_request'

    @api.depends('sign_template_id')
    def _compute_responsible_ids(self):
        for template in self:
            template.sign_template_responsible_ids = template.is_signature_request and template.sign_template_id.sign_item_ids.responsible_id
            template.responsible_count = len(template.sign_template_responsible_ids)

    @api.depends('sign_template_responsible_ids')
    def _compute_employee_role_id(self):
        for template in self:
            if len(template.sign_template_responsible_ids.ids) == 1:
                template.employee_role_id = template.sign_template_responsible_ids._origin
            else:
                template.employee_role_id = False
