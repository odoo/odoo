# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv

class marketing_configuration(osv.osv_memory):
    _name = 'marketing.configuration'
    _inherit = 'res.config.settings'
    _columns = {
        'module_marketing_campaign': fields.boolean('Marketing Campaigns',
                           help ="""It installs the marketing_campaign module."""),
        'module_marketing_campaign_crm_demo': fields.boolean('Demo data for the module Marketing Campaigns',
                           help ="""It installs the marketing_campaign_crm_demo module."""),
        'module_crm_profiling': fields.boolean('Track customer profile to focus your campaigns',
                           help ="""It install the crm_profiling module."""), 
    }
marketing_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: