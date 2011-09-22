# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class crm_installer(osv.osv_memory):
    _inherit = 'base.setup.installer'

    _columns = {
        'name': fields.char('Name', size=64),
        'crm_helpdesk': fields.boolean('Helpdesk', help="Manages a Helpdesk service."),
        'crm_fundraising': fields.boolean('Fundraising', help="This may help associations in their fundraising process and tracking."),
        'crm_claim': fields.boolean('Claims', help="Manages the suppliers and customers claims, including your corrective or preventive actions."),
        'import_sugarcrm': fields.boolean('Import Data from SugarCRM', help="Help you to import and update data from SugarCRM to OpenERP"),
        'crm_caldav': fields.boolean('Calendar Synchronizing', help="Helps you to synchronize the meetings with other calendar clients and mobiles."),
        'sale_crm': fields.boolean('Opportunity to Quotation', help="Create a Quotation from an Opportunity."),
        'fetchmail': fields.boolean('Fetch Emails', help="Allows you to receive E-Mails from POP/IMAP server."),
        'thunderbird': fields.boolean('Thunderbird Plug-In', help="Allows you to link your e-mail to OpenERP's documents. You can attach it to any existing one in OpenERP or create a new one."),
        'outlook': fields.boolean('MS-Outlook Plug-In', help="Allows you to link your e-mail to OpenERP's documents. You can attach it to any existing one in OpenERP or create a new one."),
        'wiki_sale_faq': fields.boolean('Sale FAQ', help="Helps you manage wiki pages for Frequently Asked Questions on Sales Application."),
        'import_google': fields.boolean('Google Import', help="Imports contacts and events from your google account."),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(crm_installer, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        #Checking sale module is installed or not
        cr.execute("SELECT * from ir_module_module where state='installed' and name = 'sale'")
        count = cr.fetchall()
        if count:
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='sale_crm']")
            for node in nodes:
                node.set('invisible', '0')
            res['arch'] = etree.tostring(doc)
        return res

crm_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
