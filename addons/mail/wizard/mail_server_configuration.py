# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class MailServerConfiguration(models.TransientModel):
    """ Before sending mail set domain name, incoming server, outgoing server.
    """
    _name = 'mail.server.configuration'
    _description = 'Email server configuration wizard'

    @api.model
    def default_get(self, fields):
        result = super(MailServerConfiguration, self).default_get(fields)
        res = self.env['mail.compose.message']._check_mail_configuration()
        result.update(res)
        return result

    alias_domain = fields.Char('Domain Name', help="If you have setup a catch-all email domain redirected to the Odoo server, enter the domain name here.")
    is_alias_domain = fields.Boolean('Check Domain Name')
    is_incoming_server = fields.Boolean('Check Incoming Server')
    is_outgoing_server = fields.Boolean('Check Outgoing Server')

    def set_mail_server(self):
        external_email_server = self.env['ir.config_parameter'].sudo().get_param("base_setup.default_external_email_server", default=False)
        if self.alias_domain:
            self.env['ir.config_parameter'].sudo().set_param("mail.catchall.domain", self.alias_domain)
            if not external_email_server:
                self.env['ir.config_parameter'].sudo().set_param("base_setup.default_external_email_server", True)
        res = self.env['mail.compose.message']._check_mail_configuration()
        try:
            mail_server_form_id = self.env.ref('mail.mail_server_configuration_wizard_form').id
        except ValueError:
            mail_server_form_id = False

        # Configure mail server
        if not all(res.values()):
            return {
                'name': _('Mail Server Configuration'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.server.configuration',
                'views': [(mail_server_form_id, 'form')],
                'view_id': mail_server_form_id,
                'target': 'new',
                'context': self.env.context
            }
        # After Mail server Configuration open composer for sending mail
        try:
            compose_form_id = self.env.ref('mail.email_compose_message_wizard_form').id
        except ValueError:
            compose_form_id = False
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': self.env.context
        }

    def action_ir_mail_server_from(self):
        ctx = self._context.copy()
        ctx.update({'custom_footer_visible': True})
        email_form_id = self.env.ref('base.ir_mail_server_form').id
        ir_mail_server = self.env['ir.mail_server'].sudo().search([])
        ir_mail_server_id = None
        if ir_mail_server:
            ir_mail_server_id = ir_mail_server[0].id
            mail_server_confirm = ir_mail_server.filtered(lambda r: r.check_connection)
            if mail_server_confirm:
                ir_mail_server_id = mail_server_confirm[0].id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ir.mail_server',
            'views': [(email_form_id, 'form')],
            'view_id': email_form_id,
            'target': 'new',
            'res_id': ir_mail_server_id,
            'context': ctx,
        }

    def action_email_server_from(self):
        ctx = self._context.copy()
        ctx.update({'custom_footer_visible': True})
        email_form_id = self.env.ref('fetchmail.view_email_server_form').id
        fetchmail_server = self.env['fetchmail.server'].sudo().search([])
        fetchmail_server_id = None
        if fetchmail_server:
            fetchmail_server_id = fetchmail_server[0].id
            mail_server_confirm = fetchmail_server.filtered(lambda r: r.state == 'done')
            if mail_server_confirm:
                fetchmail_server_id = mail_server_confirm[0].id

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fetchmail.server',
            'views': [(email_form_id, 'form')],
            'view_id': email_form_id,
            'target': 'new',
            'res_id': fetchmail_server_id,
            'context': ctx,
        }
