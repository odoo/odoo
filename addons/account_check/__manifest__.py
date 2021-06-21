##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
    'name': 'Account Check Management',
    'version': "1.0.0",
    'category': 'Accounting',
    'summary': 'Checks Management',
    'description': """
This module add checks management including functionality for own and third checks.

To see option of checks to print on accounting dashboard you need to create a report named "check_report"

NOTA: En la lógica de impresón de cheques y en general, solo se tienen en cuenta cheques pre-impresos ya que es el único requerimiento que tenemos por ahora. De requerirse, se podría implementar no pre-impreso básicamente haciendo que no se pueda editar el número y que se asigne automáticamente.
""",
    'author': 'ADHOC SA',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'account_check_printing',
    ],
    'data': [
        'data/account_payment_method_data.xml',
        'views/account_payment_view.xml',
        'wizards/account_payment_register_views.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
