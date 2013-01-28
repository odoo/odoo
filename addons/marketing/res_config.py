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

from openerp.osv import fields, osv

class marketing_config_settings(osv.osv_memory):
    _name = 'marketing.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'module_marketing_campaign': fields.boolean('Marketing campaigns',
            help="""Provides leads automation through marketing campaigns.
                Campaigns can in fact be defined on any resource, not just CRM leads.
                This installs the module marketing_campaign."""),
        'module_marketing_campaign_crm_demo': fields.boolean('Demo data for marketing campaigns',
            help="""Installs demo data like leads, campaigns and segments for Marketing Campaigns.
                This installs the module marketing_campaign_crm_demo."""),
        'module_crm_profiling': fields.boolean('Track customer profile to focus your campaigns',
            help="""Allows users to perform segmentation within partners.
                This installs the module crm_profiling."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
