# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, tools


class ResConfigSettings(models.TransientModel):
    """ Inherit the base settings to add a counter of failed email + configure
    the alias domain. """
    _inherit = 'res.config.settings'

    fail_counter = fields.Integer('Fail Mail', readonly=True)
    alias_domain = fields.Char('Alias Domain', help="If you have setup a catch-all email domain redirected to "
                               "the Odoo server, enter the domain name here.", config_parameter='mail.catchall.domain')
    restrict_template_rendering = fields.Boolean(
        'Restrict Template Rendering',
        config_parameter='mail.restrict.template.rendering',
        help='Users will still be able to render templates.\n'
        'However only Mail Template Editors will be able to create new dynamic templates or modify existing ones.')
    use_twilio_rtc_servers = fields.Boolean(
        'Use Twilio ICE servers',
        help="If you want to use twilio as TURN/STUN server provider",
        config_parameter='mail.use_twilio_rtc_servers',
    )
    twilio_account_sid = fields.Char(
        'Twilio Account SID',
        config_parameter='mail.twilio_account_sid',
    )
    twilio_account_token = fields.Char(
        'Twilio Account Auth Token',
        config_parameter='mail.twilio_account_token',
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        previous_date = datetime.datetime.now() - datetime.timedelta(days=30)

        res.update(
            fail_counter=self.env['mail.mail'].sudo().search_count([
                ('date', '>=', previous_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                ('state', '=', 'exception')]),
        )

        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param("mail.catchall.domain", self.alias_domain or '')
