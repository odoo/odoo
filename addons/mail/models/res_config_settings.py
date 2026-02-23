# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    """ Inherit the base settings to add a counter of failed email + configure
    the alias domain. """
    _inherit = 'res.config.settings'

    external_email_server_default = fields.Boolean(
        "Use Custom Email Servers",
        config_parameter='base_setup.default_external_email_server')
    fail_counter = fields.Integer('Fail Mail', compute="_compute_fail_counter")
    alias_domain_id = fields.Many2one(
        'mail.alias.domain', 'Alias Domain',
        readonly=False, related='company_id.alias_domain_id',
        help="If you have setup a catch-all email domain redirected to the Odoo server, enter the domain name here.")
    module_google_gmail = fields.Boolean('Support Gmail Authentication')
    module_microsoft_outlook = fields.Boolean('Support Outlook Authentication')
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
    sfu_server_url = fields.Char("SFU Server URL", config_parameter="mail.sfu_server_url")
    sfu_server_key = fields.Char("SFU Server key", config_parameter="mail.sfu_server_key", help="Base64 encoded key")
    email_primary_color = fields.Char(related='company_id.email_primary_color', readonly=False)
    email_secondary_color = fields.Char(related='company_id.email_secondary_color', readonly=False)

    use_klipy = fields.Boolean("Use Klipy")
    klipy_api_key = fields.Char("GIF API Key")
    tenor_api_key_deprecated = fields.Char("Tenor API key (deprecated)")
    tenor_api_key = fields.Char(
        'Tenor API key',
        config_parameter='discuss.tenor_api_key',
        help="Add a Tenor GIF API key to enable GIFs support. https://developers.google.com/tenor/guides/quickstart#setup\n"
        "/!\\ Tenor shuts down on June 30 2026, please use Klipy instead instead https://klipy.com/migrate",
    )
    tenor_content_filter = fields.Selection(
        [('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('off', 'Off')],
        string='Tenor content filter',
        help="https://developers.google.com/tenor/guides/content-filtering",
        config_parameter='discuss.tenor_content_filter',
        default='low',
    )
    tenor_gif_limit = fields.Integer(
        default=8,
        config_parameter='discuss.tenor_gif_limit',
        help="Fetch up to the specified number of GIF.",
    )
    google_translate_api_key = fields.Char(
        "Message Translation API Key",
        help="A valid Google API key is required to enable message translation. https://cloud.google.com/translate/docs/setup",
        config_parameter="mail.google_translate_api_key",
    )

    def _compute_fail_counter(self):
        previous_date = fields.Datetime.now() - datetime.timedelta(days=30)

        self.fail_counter = self.env['mail.mail'].sudo().search_count([
            ('date', '>=', previous_date),
            ('state', '=', 'exception'),
        ])

    def open_email_layout(self):
        layout = self.env.ref('mail.mail_notification_layout', raise_if_not_found=False)
        if not layout:
            raise UserError(_("This layout seems to no longer exist."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mail Layout'),
            'view_mode': 'form',
            'res_id': layout.id,
            'res_model': 'ir.ui.view',
        }

    def open_mail_templates(self):
        return self.env['ir.actions.actions']._for_xml_id('mail.action_email_template_tree_all')

    def set_values(self):
        super().set_values()
        value = f"KLIPY:{self.klipy_api_key}" if self.klipy_api_key else (self.tenor_api_key_deprecated or "")
        self.env["ir.config_parameter"].sudo().set_param("discuss.tenor_api_key", value)

    @api.model
    def get_values(self):
        res = super().get_values()
        raw = self.env["ir.config_parameter"].sudo().get_param("discuss.tenor_api_key", "")
        is_klipy = raw.startswith("KLIPY:")
        res.update({
            "klipy_api_key": raw[6:] if is_klipy else "",
            "tenor_api_key_deprecated": raw if not is_klipy else "",
        })
        return res
