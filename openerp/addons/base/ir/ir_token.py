# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
from datetime import timedelta
from urlparse import urljoin

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.exceptions import AccessError


class IrToken(models.TransientModel):

    _name = 'ir.token'
    _rec_name = 'value'

    @api.model
    def _get_random_token(self):
        """Generate a 32 char long pseudo-random string of digits

        UUID4 makes the chance of a collision (unicity constraint) highly
        unlikely due to the expiration period of 24 hours.
        """
        return uuid.uuid4().hex

    value = fields.Char(required=True, default=_get_random_token, size=32)
    res_model = fields.Char("Related Document Model", required=True,
        help="Name of the model that will process the token")
    res_id = fields.Integer("Related Document ID", required=True,
        help="ID of the record that will process the token")
    partner_id = fields.Many2one("res.partner", string="Target Contact",
        help="Optional restricted contact")

    _sql_constraints = [
        ('token_value_uniq', 'unique(value)', "Duplicated token")
    ]

    @api.model_cr
    def _transient_clean_rows_older_than(self, seconds):
        """Token have a minimum of 24 hours expiration before being cleaned up"""
        seconds = max(seconds, 24 * 60 * 60)
        return super(IrToken, self)._transient_clean_rows_older_than(seconds)

    @api.multi
    def _generate_token_url(self, route):
        """ Returns a public URL using a custom route

        :param route: URI in the form "/first/second/%s" with mandatory '%s' that
            will be replaced by the token value.
        """
        self.ensure_one()

        if "%s" not in route:
            raise ValueError(_("Invalid route format '%s', missing '%%s' to integrate token)") % route)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return urljoin(base_url, route % self.value)

    @api.model
    def _find_valid_token(self, token, res_model, res_id=False):
        """ Find a valid token based on record filters

        A token is only valid 24 hours after its creation.

        :param token: submitted token content
        :param res_model: model name of the record linked to submitted token
        :param res_id: id of the record linked to submitted token (optional)
        """
        yesterday = fields.Datetime.from_string(fields.Datetime.now()) - timedelta(days=1)
        domain = [('value', '=', token),
                  ('create_date', '>', fields.Datetime.to_string(yesterday)),
                  ('res_model', '=', res_model)]
        domain += res_id and [('res_id', '=', res_id)] or []
        return self.sudo().search(domain, limit=1)

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """ Prevent anyone but administrator to access a token

        Tokens may be linked to sensitive transactions so unrestricted access is
        prevented.
        """
        if self.env.user._is_admin():
            return True

        if raise_exception:
            raise AccessError(_("Sorry, you are not allowed to access this document."))
        else:
            return False

    @api.multi
    def check_access_rule(self, operation):
        if self.env.user._is_admin():
            return True

        raise AccessError(_("Sorry, you are not allowed to access this document."))
