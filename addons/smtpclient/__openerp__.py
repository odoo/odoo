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

{
    "name" : "Email Client",
    "version" : "1.0",
    "depends" : ["base"],
    "author" : "Tiny/Axelor",
    "description": """Email Client module that provides:
    Sending Email
    Use Multiple Server
    Multi Threading
    Multi Attachment
    """,
    "website" : "http://www.openerp.com",
    "category" : "Generic Modules",
    "init_xml" : [
    ],
    "demo_xml" : [
        "smtpclient_demo.xml"
    ],
    "update_xml" : [
        "smtpclient_view.xml",
        "serveraction_view.xml",
        "smtpclient_wizard.xml",
        "security/ir.model.access.csv",
        "smtpclient_data.xml",
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

