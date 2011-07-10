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

class marketing_installer(osv.osv_memory):
    _inherit = 'base.setup.installer'
    _columns = {
        'email_template':fields.boolean('Automated E-Mails',
            help="Helps you to design templates of emails and integrate them in your different processes."),
        'marketing_campaign':fields.boolean('Marketing Campaigns',
            help="Helps you to manage marketing campaigns and automate actions and communication steps."),
        'crm_profiling':fields.boolean('Profiling Tools',
            help="Helps you to perform segmentation of partners and design segmentation questionnaires")
    }
    _defaults = {
        'marketing_campaign': lambda *a: 1,
    }

marketing_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
