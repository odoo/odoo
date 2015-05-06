# -*- coding: utf-8 -*-

import urlparse
import datetime

from openerp import api, fields, models, tools


class BaseConfiguration(models.TransientModel):
    """ Inherit the base settings to add a counter of failed email + configure
    the alias domain. """
    _inherit = 'base.config.settings'

    fail_counter = fields.Integer('Fail Mail', readonly=True)
    alias_domain = fields.Char('Alias Domain', help="If you have setup a catch-all email domain redirected to "
                               "the Odoo server, enter the domain name here.")

    @api.multi
    def get_default_fail_counter(self):
        previous_date = datetime.datetime.now() - datetime.timedelta(days=30)
        return {
            'fail_counter': self.env['mail.mail'].sudo().search_count([('date', '>=', previous_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)), ('state', '=', 'exception')]),
        }

    @api.multi
    def get_default_alias_domain(self):
        alias_domain = self.env["ir.config_parameter"].get_param("mail.catchall.domain", default=None)
        if alias_domain is None:
            domain = self.env["ir.config_parameter"].get_param("web.base.url")
            try:
                alias_domain = urlparse.urlsplit(domain).netloc.split(':')[0]
            except Exception:
                pass
        return {'alias_domain': alias_domain or False}

    @api.multi
    def set_alias_domain(self):
        for record in self:
            self.env['ir.config_parameter'].set_param("mail.catchall.domain", record.alias_domain or '')
