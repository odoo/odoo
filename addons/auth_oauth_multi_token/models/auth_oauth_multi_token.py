# -*- coding: utf-8 -*-
# Florent de Labarre - 2016

from odoo import api, fields, models


class auth_oauth_multi_token(models.Model):
    """Class defining list of tokens"""

    _name = 'auth.oauth.multi.token'
    _description = 'OAuth2 token'
    _order = "id desc"

    oauth_access_token = fields.Char('OAuth Access Token', readonly=True, copy=False)
    user_id = fields.Many2one('res.users', 'User', required=True)
    active_token = fields.Boolean('Active')

    @api.model
    def create(self, vals):
        res = super(auth_oauth_multi_token, self).create(vals)
        user_active_token = res.user_id.oauth_access_token_ids.filtered('active_token')

        last_active_token = user_active_token & user_active_token[res.user_id.oauth_access_max_token:]

        last_active_token.write({
            'oauth_access_token': "****************************",
            'active_token': False})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
