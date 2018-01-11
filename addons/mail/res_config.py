# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import urlparse

from openerp.osv import osv, fields


class project_configuration(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'alias_domain': fields.char('Alias Domain',
                                     help="If you have setup a catch-all email domain redirected to "
                                          "the Odoo server, enter the domain name here."),
    }

    def get_default_alias_domain(self, cr, uid, ids, context=None):
        alias_domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "mail.catchall.domain", default=None, context=context)
        if alias_domain is None:
            domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.base.url", context=context)
            try:
                alias_domain = urlparse.urlsplit(domain).netloc.split(':')[0]
            except Exception:
                pass
        return {'alias_domain': alias_domain or False}

    def set_alias_domain(self, cr, uid, ids, context=None):
        config_parameters = self.pool.get("ir.config_parameter")
        for record in self.browse(cr, uid, ids, context=context):
            config_parameters.set_param(cr, uid, "mail.catchall.domain", record.alias_domain or '', context=context)
