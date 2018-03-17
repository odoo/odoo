from odoo import fields, api, models


class SchoolNewsLetter(models.TransientModel):
    _name = 'wiz.newsletter'
    news_letter_id = fields.Many2one('school.newsletter', 'Select NewsLetter', required=True)
    audience = fields.Selection([('parents', 'All Parents'),
                                 ('selected', 'Selected Parents'),
                                 ('others', 'Other Recipients')],
                                default='parents',
                                string='Select Audience',
                                required=True
                                )
    parent_ids = fields.Many2many('school.parent')

    emails = fields.Text('Emails of Other Recipients',
                         help='Enter the email addresses of the other recipients separated by commas')

    def send_newsletter(self):
        if self.audience == 'parents':
            parent_emails = []
            for parent in [student.parent_id for student in self.env['school.student'].search([('state','=','admitted')])]:
                parent.email and parent_emails.append(parent.email)
            if parent_emails:
                return
        if self.audience == 'selected':
            if self.parent_ids:
                parent_emails = [parent.email for parent in self.parent_ids]
            if parent_emails:
                return


