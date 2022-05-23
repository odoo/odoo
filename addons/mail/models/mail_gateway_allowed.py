# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, tools


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

    email = fields.Char('Email')
    email_normalized = fields.Char(
        string='Normalized Email', compute='_compute_email_normalized', store=True, index=True)

    @api.depends('email')
    def _compute_email_normalized(self):
        for record in self:
            record.email_normalized = tools.email_normalize(record.email)
