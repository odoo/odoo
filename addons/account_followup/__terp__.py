# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
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
    "name" : "Accounting follow-ups management",
    "version" : "1.0",
    "depends" : ["account"],
    "author" : "Tiny",
    "description": """
    Modules to automate letters for unpaid invoices, with multi-level recalls.

    You can define your multiple levels of recall through the menu:
        Financial Management/Configuration/Payment Terms/Follow-Ups

    Once it's defined, you can automatically prints recall every days
    through simply clicking on the menu:
        Financial_Management/Periodical_Processing/Print_Follow-Ups

    It will generate a PDF with all the letters according the the
    different levels of recall defined. You can define different policies
    for different companies.""",
    "website" : "http://tinyerp.com/module_account.html",
    "category" : "Generic Modules/Accounting",
    "init_xml" : [],
    "demo_xml" : ["followup_demo.xml"],
    "update_xml" : [
        "security/ir.model.access.csv",
        "wizard/wizard_view.xml",
        "followup_view.xml",
        "followup_report_view.xml",
    ],
    "active": False,
    "installable": True
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

