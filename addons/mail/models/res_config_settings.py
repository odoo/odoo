# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


# ir.asset resolves this URL to the attachment containing the custom bundle.
SFU_CLIENT_SOURCE_URL = "/_custom/mail/static/lib/odoo_sfu/odoo_sfu.js"
SFU_CLIENT_TARGET = "/mail/static/lib/odoo_sfu/odoo_sfu.js"


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
    use_call_server = fields.Boolean(
        "Use Call Server",
        help="If you want to use your own SFU or ICE servers for video calls.",
        config_parameter="mail.use_call_server",
    )
    use_twilio_rtc_servers = fields.Boolean(
        'Use Twilio ICE servers',
        help="If you want to use twilio as TURN/STUN server provider",
        config_parameter='mail.use_twilio_rtc_servers',
    )
    twilio_account_sid = fields.Char(
        'Account SID',
        config_parameter='mail.twilio_account_sid',
    )
    twilio_account_token = fields.Char(
        'Account Auth Token',
        config_parameter='mail.twilio_account_token',
    )
    use_sfu_server = fields.Boolean(
        'Use SFU server',
        help="If you want to setup SFU server for large group calls.",
        config_parameter="mail.use_sfu_server",
    )
    sfu_server_url = fields.Char("SFU Server URL", config_parameter="mail.sfu_server_url")
    sfu_server_key = fields.Char("SFU Server key", config_parameter="mail.sfu_server_key", help="Base64 encoded key")
    use_custom_sfu_client = fields.Boolean("Use Custom SFU Bundle")
    sfu_client_source = fields.Text(
        "SFU Client Bundle",
        help="SFU JS client bundle loaded by every SFU participant",
    )
    email_primary_color = fields.Char(related='company_id.email_primary_color', readonly=False)
    email_secondary_color = fields.Char(related='company_id.email_secondary_color', readonly=False)

    use_tenor_api = fields.Boolean(
        "Use Klipy API",
        help="If you want to use Klipy API to share GIFs in conversations.",
        config_parameter='discuss.use_klipy_api',
    )
    tenor_api_key = fields.Char(
        'Klipy API key',
        config_parameter='discuss.klipy_api_key',
        help="Add a Klipy GIF API key to enable GIFs support. https://docs.klipy.com/getting-started",
    )
    use_google_translate_api = fields.Boolean(
        "Use Google Translate API",
        help="If you want to use Google Translate API to enable message translation.",
        config_parameter='mail.use_google_translate_api',
    )
    google_translate_api_key = fields.Char(
        "Message Translation API Key",
        help="A valid Google API key is required to enable message translation. https://cloud.google.com/translate/docs/setup",
        config_parameter="mail.google_translate_api_key",
    )

    @api.model
    def get_values(self):
        values = super().get_values()
        client_asset = self._get_sfu_client_asset()
        values["use_custom_sfu_client"] = client_asset.active
        return values

    def set_values(self):
        self._save_sfu_client_asset()
        return super().set_values()

    @api.model
    def _get_sfu_client_asset(self):
        return self.env["ir.asset"].with_context(active_test=False, website_id=False).search(
            [
                ("bundle", "=", "mail.assets_odoo_sfu"),
                ("directive", "=", "replace"),
                ("path", "=", SFU_CLIENT_SOURCE_URL),
                ("target", "=", SFU_CLIENT_TARGET),
            ],
            limit=1,
        )

    def _save_sfu_client_asset(self, client_source=None):
        Attachment = self.env["ir.attachment"].with_context(website_id=False)
        Asset = self.env["ir.asset"].with_context(active_test=False, website_id=False)
        source_attachment = Attachment._get_serve_attachment(SFU_CLIENT_SOURCE_URL)
        client_asset = self._get_sfu_client_asset()
        source_provided = client_source is not None
        if not source_provided:
            client_source = (source_attachment.raw or b"").decode()
        client_asset_active = (
            self.use_call_server
            and self.use_sfu_server
            and self.use_custom_sfu_client
        )
        if client_asset_active and not client_source.strip():
            raise UserError(self.env._("Cannot activate custom SFU client without providing a source."))
        if source_provided and source_attachment:
            encoded_source = client_source.encode()
            if bytes(source_attachment.raw or b"") != encoded_source:
                source_attachment.raw = encoded_source
        elif source_provided:
            Attachment.create({
                "name": "SFU client source",
                "type": "binary",
                "url": SFU_CLIENT_SOURCE_URL,
                "mimetype": "application/javascript",
                "raw": client_source.encode(),
            })
        if client_asset:
            if client_asset.active != client_asset_active:
                client_asset.active = client_asset_active
        elif client_asset_active:
            Asset.create({
                "name": "Alternative SFU client",
                "bundle": "mail.assets_odoo_sfu",
                "directive": "replace",
                "path": SFU_CLIENT_SOURCE_URL,
                "target": SFU_CLIENT_TARGET,
            })

    def _compute_fail_counter(self):
        previous_date = fields.Datetime.now() - datetime.timedelta(days=30)

        self.fail_counter = self.env['mail.mail'].sudo().search_count([
            ('date', '>=', previous_date),
            ('state', '=', 'exception'),
        ])

    def action_open_sfu_client_source(self):
        self.ensure_one()
        Attachment = self.env["ir.attachment"].with_context(website_id=False)
        source_attachment = Attachment._get_serve_attachment(SFU_CLIENT_SOURCE_URL)
        self.sfu_client_source = (source_attachment.raw or b"").decode()
        return {
            "name": self.env._("SFU Client Bundle"),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "views": [(self.env.ref("mail.res_config_settings_view_form_sfu_client_source").id, "form")],
            "target": "new",
            "context": {"dialog_size": "extra-large"},
        }

    def action_save_sfu_client_asset(self):
        self.ensure_one()
        self._save_sfu_client_asset(self.sfu_client_source or "")
        return {"type": "ir.actions.act_window_close"}

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
