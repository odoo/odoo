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
    _name = 'base.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'module_multi_company': fields.boolean('Multi Company',
            help="""Work in multi-company environments, with appropriate security access between companies.
                This installs the module multi_company."""),
        'module_portal': fields.boolean('Activate Customer Portal',
            help="""The portal will give access to a series of documents for your  customers; his quotations, his invoices, his projects, etc."""),
        'module_share': fields.boolean('Allow Sharing Resources to External Users',
            help="""As an example, you will be able to share a project or some tasks to  your customers, or quotes/sales to several persons at your customer  company, or your agenda availabilities to your contacts."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
