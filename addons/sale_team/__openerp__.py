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
{
    'name' : 'Sale Team',
    'version' : '1.0',
    'author' : 'OpenERP SA',
    'category': 'hidden',   
    'sequence': 10,
    'summary': 'Sales Team',
    'description': """ """,
    'website': 'http://www.openerp.com',
    'depends' : ['base','web_kanban','calendar'],
    'data': ['sale_team.xml','sale_team_security.xml','res_config_view.xml','ir.model.access.csv'],
    'demo': [],
    'css': ['static/src/css/sale_team.css'],
    'installable': True,
    'auto_install': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
