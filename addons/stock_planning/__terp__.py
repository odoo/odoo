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
    "name":"Master Procurement Schedule",
    "version":"1.0",
    "author":"Tiny",
    "category":"Custom",
    "depends":["stock","sale"],
    "description": """
This module allows you to manage the planning of procurements based on sales
forecasts, confirmed orders (customers and suppliers), stock movements, etc.
You can planify expected outputs and inputs for each warehouses. It also works
to manage all kind of procurements like purchase orders. That's why it is
called Master Procurement Schedule instead of the classic Master Production
Schedule therminology.
""",
    "demo_xml":[],
    "update_xml":["security/ir.model.access.csv","stock_planning_view.xml"],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

