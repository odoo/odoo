# -*- coding: utf-8 -*-
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
    'name': 'Idea Manager',
    'version': '0.1',
    'category': 'Tools',
    'description': """This module allows your user to easily and efficiently participate in the innovation of the enterprise. It allows everybody to express ideas about different subjects. Then, others users can comment these ideas and vote for particular ideas. Each idea as a score based on the different votes. The managers can obtain an easy view on best ideas from all the users. Once installed, check the menu 'Ideas' in the 'Tools' main menu.""",
    'author': 'Tiny',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': [
        'idea_view.xml',
        'idea_workflow.xml',
        'security/idea_security.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': [],
    'installable': True,
    'certificate': '0071515601309',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
