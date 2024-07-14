# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrPayrollDeclarationMixin(models.AbstractModel):
    _inherit = 'hr.payroll.declaration.mixin'

    documents_enabled = fields.Boolean(compute='_compute_documents_enabled')
    documents_count = fields.Integer(compute='_compute_documents_count')

    def action_see_documents(self):
        documents = self.line_ids.mapped('pdf_filename')
        domain = [('name', 'in', documents)]
        return {
            'name': _('Documents'),
            'domain': domain,
            'res_model': 'documents.document',
            'type': 'ir.actions.act_window',
            'views': [(False, 'kanban'), (False, 'list'), (False, 'form')],
            'view_mode': 'tree,form',
            'context': {'searchpanel_default_folder_id': self.company_id.documents_payroll_folder_id.id}
        }

    @api.depends('line_ids')
    def _compute_documents_count(self):
        posted_documents = self.line_ids._get_posted_documents()
        grouped_data = self.env['hr.payroll.employee.declaration']._read_group(
            domain=[
                ('res_model', '=', self._name),
                ('res_id', 'in', self.ids),
                ('pdf_filename', 'in', posted_documents)],
            groupby=['res_id'],
            aggregates=['__count'])
        mapped_data = dict(grouped_data)
        for sheet in self:
            sheet.documents_count = mapped_data.get(sheet.id, 0)

    @api.depends('company_id.documents_payroll_folder_id', 'company_id.documents_hr_settings')
    def _compute_documents_enabled(self):
        for sheet in self:
            sheet.documents_enabled = sheet.company_id._payroll_documents_enabled()

    def action_post_in_documents(self):
        self.line_ids.action_post_in_documents()

    def _get_posted_mail_template(self):
        return self.env.ref('documents_hr_payroll.mail_template_new_declaration', raise_if_not_found=False)

    def _get_posted_document_owner(self, employee):
        return employee.user_id
