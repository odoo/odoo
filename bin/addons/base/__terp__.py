# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
# Copyright (c) 2008 Camptocamp SA
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
{
    "name" : "Base",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://openerp.com",
    "category" : "Generic Modules/Base",
    "description": "The kernel of OpenERP, needed for all installation.",
    "depends" : [],
    "init_xml" : [
        "base_data.xml",
        "base_menu.xml",
        "security/base_security.xml",
        "res/res_security.xml",
    ],
    "demo_xml" : [
        "base_demo.xml",
        "res/partner/partner_demo.xml",
        "res/partner/crm_demo.xml",
    ],
    "update_xml" : [
        "base_update.xml",
        "ir/wizard/wizard_menu_view.xml",
        "ir/ir.xml",
        "ir/workflow/workflow_view.xml",
        "module/module_data.xml",
        "module/module_wizard.xml",
        "module/module_view.xml",
        "module/module_report.xml",
        "res/res_request_view.xml",
        "res/res_lang_view.xml",
        "res/partner/partner_report.xml",
        "res/partner/partner_view.xml",
        "res/partner/partner_wizard.xml",
        "res/bank_view.xml",
        "res/country_view.xml",
        "res/res_currency_view.xml",
        "res/partner/crm_view.xml",
        "res/partner/partner_data.xml",
        "res/ir_property_view.xml",
        "security/base_security.xml",
        "security/ir.model.access.csv",
    ],
    "active": True,
    "installable": True,
}
