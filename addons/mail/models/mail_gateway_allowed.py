# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import _, api, fields, models, tools


class MailGatewayAllowed(models.Model):
    """List of trusted email address which won't have the quota restriction.

    The incoming emails have a restriction of the number of records they can
    create with alias, defined by the 2 systems parameters;
    - mail.gateway.loop.minutes
    - mail.gateway.loop.threshold

    But we might have some legit use cases for which we want to receive a ton of emails
    from an automated-source. This model stores those trusted source and this restriction
    won't apply to them.
    """

    _description = 'Mail Gateway Allowed'
    _name = 'mail.gateway.allowed'

    email = fields.Char('Email Address', required=True)
    email_normalized = fields.Char(
        string='Normalized Email', compute='_compute_email_normalized', store=True, index=True)

    @api.depends('email')
    def _compute_email_normalized(self):
        for record in self:
            record.email_normalized = tools.email_normalize(record.email)

    @api.model
    def get_empty_list_help(self, help_message):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        LOOP_MINUTES = int(get_param('mail.gateway.loop.minutes', 120))
        LOOP_THRESHOLD = int(get_param('mail.gateway.loop.threshold', 20))

        return Markup(_('''
            <p class="o_view_nocontent_smiling_face">
                Add addresses to the Allowed List
            </p><p>
                To protect you from spam and reply loops, Odoo automatically blocks emails
                coming to your gateway past a threshold of <b>%(threshold)i</b> emails every <b>%(minutes)i</b>
                minutes. If there are some addresses from which you need to receive very frequent
                updates, you can however add them below and Odoo will let them go through.
            </p>''')) % {
            'threshold': LOOP_THRESHOLD,
            'minutes': LOOP_MINUTES,
        }
