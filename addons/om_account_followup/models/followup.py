# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FollowupFollowup(models.Model):
    _name = 'followup.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'

    name = fields.Char(string="Name", related='company_id.name', readonly=True)
    followup_line = fields.One2many('followup.line', 'followup_id', 'Follow-up', copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [('company_uniq', 'unique(company_id)',
                         'Only one follow-up per company is allowed')]


class FollowupLine(models.Model):
    _name = 'followup.line'
    _description = 'Follow-up Criteria'
    _order = 'delay'

    def _compute_sequence(self):
        delays = [line.delay for line in self.followup_id.followup_line]
        delays.sort()
        for line in self.followup_id.followup_line:
            sequence = delays.index(line.delay)
            line.sequence = sequence+1

    @api.model
    def default_get(self, default_fields):
        values = super(FollowupLine, self).default_get(default_fields)
        if self.env.ref('om_account_followup.email_template_om_account_followup_default'):
            values['email_template_id'] = self.env.ref('om_account_followup.email_template_om_account_followup_default').id
        return values

    name = fields.Char('Follow-Up Action', required=True)
    sequence = fields.Integer('Sequence', compute='_compute_sequence',
                              store=False,
                              help="Gives the sequence order when displaying a list of follow-up lines.")
    followup_id = fields.Many2one('followup.followup', 'Follow Ups',
                                  required=True, ondelete="cascade")
    delay = fields.Integer('Due Days',
                           help="The number of days after the due date of the "
                                "invoice to wait before sending the reminder. Could be negative if you want "
                                "to send a polite alert beforehand.",
                           required=True)
    description = fields.Text('Printed Message', translate=True, default="""
        Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following
amount stays unpaid. Please, take appropriate measures in order to carry out
this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please
ignore this message. Do not hesitate to contact our accounting department.

Best Regards,
""", )
    send_email = fields.Boolean('Send an Email', default=True,
                                help="When processing, it will send an email")
    send_letter = fields.Boolean('Send a Letter', default=True,
                                 help="When processing, it will print a letter")
    manual_action = fields.Boolean('Manual Action', default=False,
                                   help="When processing, it will set the "
                                        "manual action to be taken for that customer. ")
    manual_action_note = fields.Text('Action To Do')
    manual_action_responsible_id = fields.Many2one('res.users',
                                                   string='Assign a Responsible', ondelete='set null')
    email_template_id = fields.Many2one('mail.template', 'Email Template',
                                        ondelete='set null')

    _sql_constraints = [('days_uniq', 'unique(followup_id, delay)',
                         'Days of the follow-up levels must be different')]

    @api.constrains('description')
    def _check_description(self):
        for line in self:
            if line.description:
                try:
                    line.description % {'partner_name': '', 'date': '',
                                        'user_signature': '',
                                        'company_name': ''}
                except ValidationError:
                    raise ValidationError(
                        _('Your description is invalid, use the right legend '
                          'or %% if you want to use the percent character.'))
