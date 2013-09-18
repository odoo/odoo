# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################


{
    'name': 'Applicant Resumes and Letters',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 25,
    'summary': 'Search job applications by Index content.',
    'description': """
    This module allows you to search job applications by Index content
    of Resumes & Letters.
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': [],
    'depends': ['hr_recruitment','document'],
    'data': ['hr_applicant_document_view.xml'],
    'demo': ['hr_applicant_document_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': True,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
