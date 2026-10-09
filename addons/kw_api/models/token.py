import hashlib
import logging
import os
from datetime import timedelta

from odoo import fields, models, api, _

from ..controllers.controller_base import KwApiError

_logger = logging.getLogger(__name__)


class Token(models.Model):
    _name = 'kw.api.token'
    _inherit = ['kw.api.model.mixin', ]
    _description = 'API Token'

    name = fields.Char(
        string='Token', required=True, )
    user_id = fields.Many2one(
        comodel_name='res.users', required=True, )
    expire_date = fields.Datetime(
        required=True, )
    is_expired = fields.Boolean(
        compute='_compute_is_expired', )
    refresh_token = fields.Char(
        required=True, )
    refresh_token_expire_date = fields.Datetime(
        required=True, )
    is_refresh_token_expired = fields.Boolean(
        compute='_compute_is_expired', )

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', _('Token must be unique')),
        ('refresh_token_uniq', 'UNIQUE(refresh_token)',
         _('Refresh token must be unique')), ]

    def _compute_is_expired(self):
        for obj in self:
            obj.is_expired = obj.expire_date < fields.Datetime.now() \
                if obj.expire_date else True
            if not obj.refresh_token_expire_date:
                obj.is_refresh_token_expired = True
            else:
                obj.is_refresh_token_expired = \
                    obj.refresh_token_expire_date < fields.Datetime.now()

    @api.model
    def generate_token_string(self):
        token_length = int(self.env['ir.config_parameter'].sudo(
        ).get_param('kw_api.kw_api_token_length')) or 40
        prefix = self.env['ir.config_parameter'].sudo(
        ).get_param('kw_api.kw_api_token_prefix') or ''
        r_bytes = os.urandom(token_length)
        return '{}{}'.format(prefix, str(hashlib.sha256(r_bytes).hexdigest()))

    @api.model
    def refresh_token_by_refresh_token(self, refresh_token):
        obj = self.search([('refresh_token', '=', refresh_token)], limit=1)
        if not obj:
            raise KwApiError('auth_error', _('Wrong token'))
        obj.update_token(both=True)
        return obj

    def update_token(self, both=False):
        expire_hours = int(self.env['ir.config_parameter'].sudo(
        ).get_param('kw_api.kw_api_token_expire_hours'))
        refresh_expire_hours = int(self.env['ir.config_parameter'].sudo(
        ).get_param('kw_api.kw_api_refresh_token_expire_hours'))
        for obj in self:
            data = {
                'name': self.generate_token_string(),
                'expire_date':
                    fields.Datetime.now() + timedelta(hours=expire_hours), }
            if not obj.refresh_token or both:
                data['refresh_token'] = self.generate_token_string()
                data['refresh_token_expire_date'] = \
                    fields.Datetime.now() + timedelta(
                        hours=refresh_expire_hours)
            obj.write(data)

    @api.model
    def default_get(self, vals):
        expire_hours = int(self.env['ir.config_parameter'].sudo(
        ).get_param('kw_api.kw_api_token_expire_hours'))
        refresh_expire_hours = int(self.env['ir.config_parameter'].sudo(
        ).get_param('kw_api.kw_api_refresh_token_expire_hours'))
        res = super().default_get(vals)
        res['name'] = self.generate_token_string()
        res['expire_date'] = \
            fields.Datetime.now() + timedelta(hours=expire_hours)
        res['refresh_token_expire_date'] = \
            fields.Datetime.now() + timedelta(hours=refresh_expire_hours)
        res['refresh_token'] = self.generate_token_string()
        return res

    def kw_api_get_record_value(self):
        self.ensure_one()
        return {
            'name': self.name,
            'user_id': self.user_id.id,
            'expire_date': self.expire_date,
            'is_expired': self.is_expired,
            'refresh_token': self.refresh_token,
            'refresh_token_expire_date': self.refresh_token_expire_date,
            'is_refresh_token_expired': self.is_refresh_token_expired, }

    @api.model
    def create(self, vals_list):
        if bool(self.env['ir.config_parameter'].sudo().get_param(
                'kw_api.kw_api_one_token_per_user')):
            self.search([('user_id', '=', vals_list.get('user_id'))]).unlink()
        return super().create(vals_list)
