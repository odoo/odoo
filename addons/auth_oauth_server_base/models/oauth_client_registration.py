from odoo import api, fields, models


class OauthClientRegistration(models.TransientModel):
    _name = 'oauth.client.registration'
    _description = 'Register an OAuth Client'

    client_name = fields.Char(
        string="Client Name", required=True,
        help="Shown to the user on the consent screen.",
    )
    resource_id = fields.Many2one(
        'oauth.resource', string="Resource", required=True,
        help="The protected resource this client is being granted access to.",
    )
    client_type = fields.Selection(
        [('public', 'Public'), ('confidential', 'Confidential')],
        required=True, default='confidential',
        help="A confidential application will receive both a client id and secret whereas a public one "
             "will only receive a client id.",
    )
    redirect_uris = fields.Text(
        required=True,
        help="One redirect URI per line. Must be HTTPS, except for http:// loopback URIs.",
    )

    @api.constrains('redirect_uris')
    def _check_redirect_uris(self):
        for registration in self:
            redirect_uris = [uri.strip() for uri in registration.redirect_uris.splitlines() if uri.strip()]
            self.env['oauth.client']._validate_redirect_uris(redirect_uris)

    def action_register(self):
        self.ensure_one()
        credentials = self.env['oauth.client']._register_client(
            self.resource_id,
            self.client_name,
            [uri.strip() for uri in self.redirect_uris.splitlines() if uri.strip()],
            self.client_type,
        )
        client_secret = credentials.get('client_secret')
        if not client_secret:
            return {'type': 'ir.actions.act_window_close'}

        return self.env['oauth.client.secret.show']._show(client_secret)
