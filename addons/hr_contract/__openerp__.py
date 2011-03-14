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
    'name': 'Human Resources Contracts',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
    Add all information on the employee form to manage contracts.
    =============================================================
    * Marital status,
    * Security number,
    * Place of birth, birth date, ...
    You can assign several contracts per employee.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/hr_contract.jpeg'],
    'depends': ['hr'],
    'init_xml': ['hr_contract_data.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'hr_contract_view.xml'
        ],
    'demo_xml': [],
    'test': ['test/test_hr_contract.yml'],
    'installable': True,
    'active': False,
    'certificate': '0046298028637',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
