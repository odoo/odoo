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
from lxml import etree
from osv import fields, osv

class profile_association_config_install_modules_wizard(osv.osv_memory):
    _inherit = 'base.setup.installer'

    _columns = {
        'hr_expense':fields.boolean('Resources Management: Expenses Tracking',  help="Tracks and manages employee expenses, and can "
                 "automatically re-invoice clients if the expenses are "
                 "project-related."),
        'event_project':fields.boolean('Event Management: Events', help="Helps you to manage and organize your events."),
        'project_gtd':fields.boolean('Getting Things Done',
            help="GTD is a methodology to efficiently organise yourself and your tasks. This module fully integrates GTD principle with OpenERP's project management."),
        'wiki': fields.boolean('Wiki', help="Lets you create wiki pages and page groups in order "
                 "to keep track of business knowledge and share it with "
                 "and  between your employees."),
    }

    # Will be removed when rd-v61-al-config-depends will be done
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(profile_association_config_install_modules_wizard, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        for module in ['project_gtd','hr_expense']:
            count = 0
            for node in doc.xpath("//field[@name='%s']" % (module)):
                count = count + 1
                if count > 1:
                    node.set('invisible', '1')
        res['arch'] = etree.tostring(doc)
        return res
   
profile_association_config_install_modules_wizard()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
