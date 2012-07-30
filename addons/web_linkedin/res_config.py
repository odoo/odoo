# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class base_config_settings(osv.osv_memory):
    _inherit = 'base.config.settings'
    _name = 'base.config.settings'
    _columns = {
        'default_linkedin_api_key': fields.char('LinkedIn API key', size=128, default_model='res.company',
                help="""Give API key of linkedin."""),
        'generate_key': fields.text('Go to URL', readonly=True,
                help="""If you have not generate linkedin API Key yet than Go to URL to generate and enter it in above text field."""),
    }
    _defaults = {
        'generate_key': "To find contact persons from LinkedIn "\
                        "\n====================================="\
                        "\n* Go to this URL : https://www.linkedin.com/secure/developer  "\
                        "\n* Add New Application and fill the form,"\
                        "\n    - JavaScript API Domain is Your domain name (e.g. https://yourcompany.my.openerp.com),"\
                        "\n    - You can give multiple domain (e.g. yourcompany.my.openerp.com),"\
                        "\n    - programming tools is Javascript"\
                        '\n* Copy the "API Key" and paste it in the field "LinkedIn API Key" here above.'
    }

    def execute(self, cr, uid, ids, context=None):
        super(base_config_settings,self).execute(cr, uid, ids, context=context)
        company_obj = self.pool.get('res.company')
        data = self.browse(cr, uid, ids[0], context=context)
        company_id = company_obj._company_default_get(cr, uid, 'res.users', context=context)
        company_obj.write(cr, uid, [company_id], {'linkedin_api_key': data.default_linkedin_api_key}, context=context)

base_config_settings()


