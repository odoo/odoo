# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import ormcache


class IrConfigParameter(models.Model):
    _name = 'ir.config_parameter'
    _inherit = 'ir.config_parameter'

    _KEYS = ('mail.catchall.alias',
             'mail.catchall.domain',
             'mail.bounce.alias',
             'mail.session.batch.size',
             'mail.batch_size',
             'web.base.url')

    @api.model
    def get_param(self, key, default=False):
        if key in self._KEYS:
            return self._get_mail_params().get(key, default)
        return super(IrConfigParameter, self).get_param(key, default=default)

    @ormcache('self.env.uid')
    def _get_mail_params(self):
        params = self.env['ir.config_parameter'].search_read([
            ('key', 'in', self._KEYS)], fields=['key', 'value'])
        return dict((param['key'], param['value']) for param in params)
