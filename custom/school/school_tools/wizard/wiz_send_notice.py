from odoo import fields, api, models


class SchoolNotice(models.TransientModel):
    _name = 'wiz.notice'
    notice_id = fields.Many2one('school.notice', 'Select Notice')
    notice = fields.Char('Type notice instead')
    notice_type = fields.Selection([('existing', 'Existing'),
                                    ('quick', 'Quick Notice')],
                                   default='existing',
                                   string='Notice Type',
                                   required=True)
    send_via = fields.Selection([('sms', 'SMS'),
                                 ('email', 'Email'),
                                 ('both', 'Both')],
                                default='sms',
                                string='Send notice via',
                                required=True
                                )
    audience = fields.Selection([('parents', 'All Parents'),
                                 ('teachers', 'All Teachers'),
                                 ('selected', 'Selected Parents'),
                                 ('others', 'Other Recipients')],
                                default='parents',
                                string='Select Audience',
                                required=True
                                )
    parent_ids = fields.Many2many('school.parent')

    emails = fields.Text('Emails of Other Recipients',
                         help='Enter the email addresses of the other recipients separated by commas')
    phone_numbers = fields.Text('Phone Numbers of Other Recipients',
                         help='Enter the Phone numbers of the other recipients separated by commas')

    def send_notice(self):
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


