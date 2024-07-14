# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.addons.sign.controllers.main import Sign
from odoo.http import request


class SignContract(Sign):

    @http.route()
    def sign(self, sign_request_id, token, sms_token=False, signature=None, **kwargs):
        result = super().sign(sign_request_id, token, sms_token=sms_token, signature=signature, **kwargs)
        request_item = request.env['sign.request.item'].sudo().search([('access_token', '=', token)])
        is_completed = all(state == 'completed' for state in request_item.sign_request_id.request_item_ids.mapped('state'))
        signature_request_tag = request.env.ref('documents_hr_contract.document_tag_signature_request', raise_if_not_found=False)
        if not is_completed:
            return result

        employee = request.env['hr.employee'].sudo().with_context(active_test=False).search([
            ('sign_request_ids', 'in', request_item.sign_request_id.ids)])
        if employee and employee.company_id.documents_hr_folder and employee.company_id.documents_hr_settings:
            sign_request_sudo = request_item.sign_request_id.sudo()
            sign_request_sudo._generate_completed_document()

            employee_partner = employee.work_contact_id or employee.user_id.partner_id
            owner = employee.user_id
            if not owner:
                owner = employee.search([('work_contact_id', '=', employee_partner.id)]).user_id
            if not owner:
                owner = employee.contract_id.hr_responsible_id

            request.env['documents.document'].sudo().create({
                'partner_id': employee_partner.id,
                'owner_id': owner.id,
                'datas': sign_request_sudo.completed_document,
                'name': sign_request_sudo.display_name,
                'folder_id': employee.company_id.documents_hr_folder.id,
                'tag_ids': [(4, signature_request_tag.id)] if signature_request_tag else [],
                'res_id': employee.id,
                'res_model': 'hr.employee',  # Security Restriction to contract managers
            })

        contract = request.env['hr.contract'].sudo().with_context(active_test=False).search([
            ('sign_request_ids', 'in', request_item.sign_request_id.ids)])
        if contract:
            sign_request_folder = contract._get_sign_request_folder()
            if sign_request_folder and contract.company_id.documents_hr_settings:
                sign_request_sudo = request_item.sign_request_id.sudo()
                sign_request_sudo._generate_completed_document()

                employee = contract.employee_id
                employee_partner = employee.work_contact_id or employee.user_id.partner_id
                owner = employee.user_id
                if not owner:
                    owner = employee.search([('work_contact_id', '=', employee_partner.id)]).user_id
                if not owner:
                    owner = employee.contract_id.hr_responsible_id

                request.env['documents.document'].sudo().create({
                    'partner_id': employee_partner.id,
                    'owner_id': owner.id,
                    'datas': sign_request_sudo.completed_document,
                    'name': sign_request_sudo.display_name,
                    'folder_id': sign_request_folder.id,
                    'tag_ids': [(4, signature_request_tag.id)] if signature_request_tag else [],
                    'res_id': contract.id,
                    'res_model': 'hr.contract',  # Security Restriction to contract managers
                })
        return result
