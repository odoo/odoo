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
{
    "name" : "Purchase Requisitions",
    "version" : "0.1",
    "author" : "OpenERP SA",
    "category" : "Purchase Management",
    "images" : ['images/purchase_requisitions.jpeg'],
    "website" : "http://www.openerp.com",
    "description": """
This module allows you to manage your Purchase Requisition.
===========================================================

When a purchase order is created, you now have the opportunity to save the related requisition.
This new object will regroup and will allow you to easily keep track and order all your purchase orders.
""",
    "depends" : ["purchase","mrp"],
    "init_xml" : [],
    "demo_xml" : ['purchase_requisition_demo.xml'],
    "update_xml" : ["security/purchase_tender.xml",
                    "wizard/purchase_requisition_partner_view.xml",
                    "purchase_requisition_data.xml",
                    "purchase_requisition_view.xml",
                    "purchase_requisition_report.xml",
                    "security/ir.model.access.csv","purchase_requisition_sequence.xml"
    ],
    "auto_install": False,
    "test":[
            'test/purchase_requisition_demo.yml',
            'test/purchase_requisition.yml',
            'test/cancel_purchase_requisition.yml',
            ],
    "installable": True,
    "certificate" : "001023264099823179629",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

