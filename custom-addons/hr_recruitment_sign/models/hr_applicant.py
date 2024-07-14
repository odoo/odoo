# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError


class Applicant(models.Model):
    _inherit = 'hr.applicant'

    sign_request_count = fields.Integer(related="partner_id.signature_count")

    def _send_applicant_sign_request(self):
        self.ensure_one()

        # if an applicant does not already has associated partner_id create it
        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('You must define a Contact Name for this applicant.'))
            self.partner_id = self.env['res.partner'].create({
                'is_company': False,
                'name': self.partner_name,
                'email': self.email_from,
                'phone': self.partner_phone,
                'mobile': self.partner_mobile
            })

        action = self.env['ir.actions.actions']\
            ._for_xml_id('hr_recruitment_sign.sign_recruitment_wizard_action')
        action['context'] = {'default_applicant_id': self.id}
        return action

    def open_applicant_sign_requests(self):
        self.ensure_one()
        if self.partner_id:
            request_ids = self.env['sign.request.item'].search([
                ('partner_id', '=', self.partner_id.id)]).sign_request_id
            if self.env.user.has_group('sign.group_sign_user'):
                view_id = self.env.ref("sign.sign_request_view_kanban").id
            else:
                view_id = self.env.ref("hr_contract_sign.sign_request_employee_view_kanban").id

            return {
                'type': 'ir.actions.act_window',
                'name': _('Signature Requests'),
                'view_mode': 'kanban,tree',
                'res_model': 'sign.request',
                'view_ids': [(view_id, 'kanban'), (False, 'tree')],
                'domain': [('id', 'in', request_ids.ids)]
            }

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        request_ids = self.env['sign.request.item'].search([
            ('partner_id', '=', self.partner_id.id)]).sign_request_id
        vals['sign_request_ids'] = request_ids.ids
        return vals

    def _update_employee_from_applicant(self):
        for applicant in self:
            request_ids = self.env['sign.request.item'].search([
                ('partner_id', '=', applicant.partner_id.id)]).sign_request_id
            applicant.emp_id.sign_request_ids |= request_ids
        return super()._update_employee_from_applicant()
