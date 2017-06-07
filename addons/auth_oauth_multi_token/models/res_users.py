# -*- coding: utf-8 -*-
# Florent de Labarre - 2016

import openerp
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    oauth_access_token_ids = fields.One2many('auth.oauth.multi.token', 'user_id', 'Tokens', copy=False)
    oauth_access_max_token = fields.Integer('Number of simultaneous connections', default=5, required=True, copy=False)

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        res = super(ResUsers, self)._auth_oauth_signin(provider, validation, params)

        oauth_uid = validation['user_id']
        user_ids = self.search([('oauth_uid', '=', oauth_uid), ('oauth_provider_id', '=', provider)]).ids
        if not user_ids:
            raise openerp.exceptions.AccessDenied()
        assert len(user_ids) == 1

        self.oauth_access_token_ids.create({'user_id': user_ids[0],
                                            'oauth_access_token': params['access_token'],
                                            'active_token': True,
                                            })
        return res

    @api.multi
    def clear_token(self):
        for users in self:
            for token in users.oauth_access_token_ids:
                token.write({
                    'oauth_access_token': "****************************",
                    'active_token': False})

    @api.model
    def check_credentials(self, password):
        try:
            return super(ResUsers, self).check_credentials(password)
        except openerp.exceptions.AccessDenied:
            res = self.env['auth.oauth.multi.token'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('oauth_access_token', '=', password),
                ('active_token', '=', True),
            ], limit=1)
            if not res:
                raise

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
