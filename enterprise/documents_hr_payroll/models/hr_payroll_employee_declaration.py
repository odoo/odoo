# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError


class HrPayrollEmployeeDeclaration(models.Model):
    _inherit = 'hr.payroll.employee.declaration'

    pdf_to_post = fields.Boolean()
    state = fields.Selection(
        selection_add=[
            ('pdf_to_post', 'Queued PDF posting'),
            ('pdf_posted', 'Posted PDF')
        ], ondelete={'pdf_to_post': 'set pdf_generated', 'pdf_posted': 'set pdf_generated'})
    document_id = fields.Many2one('documents.document')

    @api.depends('pdf_to_post', 'document_id')
    def _compute_state(self):
        super()._compute_state()
        for declaration in self:
            if declaration.pdf_to_post:
                declaration.state = 'pdf_to_post'
            elif declaration.document_id:
                declaration.state = 'pdf_posted'

    def _get_posted_documents(self):
        document_data = self.env['documents.document']._read_group([
            ('name', 'in', [line.pdf_filename for line in self]), ('active', '=', True)],
            groupby=['name'], aggregates=['__count'])
        mapped_data = dict(document_data)
        return [posted_filename for posted_filename in mapped_data if mapped_data[posted_filename] > 0]

    def _post_pdf(self):
        create_vals = []
        posted_documents = self._get_posted_documents()
        odoobot = self.env.ref('base.user_root')
        lines_to_post = self.env['hr.payroll.employee.declaration']
        for line in self:
            template = self.env[line.res_model]._get_posted_mail_template()
            if line.pdf_filename not in posted_documents and line.pdf_file:
                lines_to_post += line
                partner_id = self.env[line.res_model]._get_posted_document_owner(line.employee_id).partner_id.id
                folder = line.company_id.documents_payroll_folder_id
                access_ids = {}
                if (partner_id
                        and partner_id not in (v['partner_id'] for v in folder._get_inherited_access_ids_vals())):
                    access_ids = {'access_ids': [Command.create({'partner_id': partner_id, 'role': 'view'})]}
                create_vals.append({
                    'owner_id': odoobot.id,
                    **access_ids,
                    'partner_id': partner_id or False,
                    'datas': line.pdf_file,
                    'name': line.pdf_filename,
                    'folder_id': folder.id,
                    'res_model': 'hr.payslip',  # Security Restriction to payroll managers
                })
                if template:
                    template.send_mail(line.employee_id.id, email_layout_xmlid='mail.mail_notification_light')

        posted_documents = self.env['documents.document'].create(create_vals)
        for line_to_post, posted_document in zip(lines_to_post, posted_documents):
            line_to_post.document_id = posted_document

    @api.model_create_multi
    def create(self, vals_list):
        declarations = super().create(vals_list)
        if any(declaration.pdf_to_post for declaration in declarations):
            self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
        return declarations

    def write(self, vals):
        res = super().write(vals)
        if vals.get('pdf_to_post'):
            self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
        return res

    def action_post_in_documents(self):
        for company in self.company_id:
            if not company._payroll_documents_enabled():
                raise UserError(_('Document posting is not properly set in configuration'))
        self.write({'pdf_to_post': True})
        self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("PDFs are going to be posted in Documents shortly"),
            }
        }
