# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class hr_employee(models.Model):
    _inherit = "hr.employee"

    newly_hired_employee = fields.Boolean('Newly hired employee', compute='_compute_newly_hired_employee',
                                          search='_search_newly_hired_employee')

    @api.multi
    def _compute_newly_hired_employee(self):
        read_group_result = self.env['hr.applicant'].read_group(
            [('emp_id', 'in', self.ids), ('job_id.state', '=', 'recruit')],
            ['emp_id'], ['emp_id'])
        result = dict((data['emp_id'], data['emp_id_count'] > 0) for data in read_group_result)
        for record in self:
            record.newly_hired_employee = result.get(record.id, False)

    def _search_newly_hired_employee(self, operator, value):
        applicants = self.env['hr.applicant'].search([('job_id.state', '=', 'recruit')])
        return [('id', 'in', applicants.ids)]

    @api.multi
    def _broadcast_welcome(self):
        """ Broadcast the welcome message to all users in the employee company. """
        self.ensure_one()
        IrModelData = self.env['ir.model.data']
        channel_all_employees = IrModelData.xmlid_to_object('mail.channel_all_employees')
        template_new_employee = IrModelData.xmlid_to_object('hr_recruitment.hr_welcome_new_employee')
        if template_new_employee:
            MailTemplate = self.env['mail.template']
            body_html = MailTemplate.render_template(template_new_employee.body_html, 'hr.employee', self.id)
            subject = MailTemplate.render_template(template_new_employee.subject, 'hr.employee', self.id)
            channel_all_employees.message_post(
                body=body_html, subject=subject,
                subtype='mail.mt_comment')
        return True
