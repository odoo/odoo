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
    'name': 'Ideas Box',
    'version': '0.1',
    'category': 'Human Resources',
    'complexity': "easy",
    'description': """
This module allows your user to easily and efficiently participate in enterprise innovation.
============================================================================================

It allows everybody to express ideas about different subjects.
Then, other users can comment on these ideas and vote for particular ideas.
Each idea has a score based on the different votes.
The managers can obtain an easy view of best ideas from all the users.
Once installed, check the menu 'Ideas' in the 'Tools' main menu.""",
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['base_tools'],
    'init_xml': [],
    'update_xml': [
        'security/idea_security.xml',
        'security/ir.model.access.csv',
        'wizard/idea_post_vote_view.xml',
        'idea_view.xml',
        'idea_workflow.xml',
        'report/report_vote_view.xml',
    ],
    'demo_xml': [
        "idea_data.xml"
    ],
    'test':[
        'test/test_idea.yml'
    ],
    'installable': True,
    'certificate': '0071515601309',
    'images': ['images/1_ideas.jpeg','images/2_idea_categories.jpeg','images/3_vote_idea.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
