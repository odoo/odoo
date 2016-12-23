# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright Eezee-It
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
    'name': 'BE Coda Sequence',
    'version': '0.1',
    'license': 'AGPL-3',
    'author': 'Eezee-It',
    'category': 'Accounting',
    'description': """
BE CODA Sequence
    """,
    'depends': [
        'account', 'l10n_be_coda', 'account_bank_statement_extensions',
    ],
    'data': [
        'views/account_bank_statement.xml',
        'views/account_bank_statement_line.xml',
        'views/account_journal.xml',
        'views/l10n_be_coda_sequence_installer.xml',
    ],
    'demo': [
        'demo/account_fiscalyear.xml',
        'demo/account_period.xml',
        'demo/ir_sequence.xml',
        'demo/account_journal.xml',
        'demo/res_partner_bank.xml',
    ],
}
