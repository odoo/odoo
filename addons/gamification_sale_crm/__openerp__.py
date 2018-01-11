# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://openerp.com>).
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
    'name': 'CRM Gamification',
    'version': '1.0',
    'author': 'OpenERP SA',
    'category': 'hidden',
    'depends': ['gamification','sale_crm'],
    'website' : 'https://www.odoo.com/page/gamification',
    'description': """Example of goal definitions and challenges that can be used related to the usage of the CRM Sale module.""",
    'data': ['sale_crm_goals.xml'],
    'demo': ['sale_crm_goals_demo.xml'],
    'auto_install': True,
}
