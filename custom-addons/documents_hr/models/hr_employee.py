# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'documents.mixin']

    document_count = fields.Integer(compute='_compute_document_count')
    documents_share_id = fields.Many2one('documents.share', readonly=True, groups="hr.group_hr_manager")

    def _get_document_folder(self):
        return self.company_id.documents_hr_folder if self.company_id.documents_hr_settings else False

    def _get_document_owner(self):
        return self.user_id

    def _get_document_partner(self):
        return self.work_contact_id

    def _check_create_documents(self):
        return self.company_id.documents_hr_settings and super()._check_create_documents()

    def _get_employee_document_domain(self):
        self.ensure_one()
        user_domain = [('partner_id', '=', self.work_contact_id.id)]
        if self.user_id:
            user_domain = expression.OR([user_domain,
                                        [('owner_id', '=', self.user_id.id)]])
        return user_domain

    def _compute_document_count(self):
        # Method not optimized for batches since it is only used in the form view.
        for employee in self:
            if employee.work_contact_id:
                employee.document_count = self.env['documents.document'].search_count(
                    employee._get_employee_document_domain())
            else:
                employee.document_count = 0

    def action_open_documents(self):
        self.ensure_one()
        if not self.work_contact_id:
            # Prevent opening documents if the employee's address is not set or no user is linked.
            raise ValidationError(_('You must set a work contact address on the Employee in order to use Document\'s features.'))
        hr_folder = self._get_document_folder()
        action = self.env['ir.actions.act_window']._for_xml_id('documents.document_action')
        # Documents created within that action will be 'assigned' to the employee
        # Also makes sure that the views starts on the hr_holder
        action['context'] = {
            'default_partner_id': self.work_contact_id.id,
            'searchpanel_default_folder_id': hr_folder and hr_folder.id,
        }
        action['domain'] = self._get_employee_document_domain()
        return action

    def action_send_documents_share_link(self):
        invalid_employees = self.filtered(lambda e: not (e.private_email and e.user_id))
        if invalid_employees:
            raise UserError(_('Employee\'s related user and private email must be set to use \"Send Access Link\" function:\n%s', '\n'.join(invalid_employees.mapped('name'))))
        template = self.env.ref('documents_hr.mail_template_document_folder_link', raise_if_not_found=False)
        for employee in self:
            if not employee.documents_share_id or (employee.documents_share_id.owner_id != employee.user_id):
                employee.documents_share_id = self.env['documents.share'].create({
                    'folder_id': self.env.company.documents_hr_folder.id,
                    'include_sub_folders': True,
                    'name': _('HR Documents: %s', employee.name),
                    'type': 'domain',
                    'domain': "[('owner_id', '=', %s)]" % (employee.user_id.id),
                    'action': 'download',
                    'owner_id': employee.user_partner_id.id,
                })
            if template:
                template.send_mail(
                    employee.id, force_send=True,
                    email_values={'model': False, 'res_id': False},
                    email_layout_xmlid='mail.mail_notification_light')
                employee.message_post(body=_('The access link has been sent to the employee.'))
