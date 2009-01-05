# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name":"Dashboard for sales",
    "version":"1.0",
    "author":"Tiny",
    "category":"Board/Sales & Purchase",
    "depends":["board","sale", "report_crm", "report_sale"],
    "demo_xml":["board_sale_demo.xml"],
    "update_xml":["board_sale_view.xml"],
    "description": """
This module implements a dashboard for salesman that includes:
    * You open quotations
    * Top 10 sales of the month
    * Cases statistics
    * Graph of sales by product
    * Graph of cases of the month
    """,
    "active":False,
    "installable":True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

