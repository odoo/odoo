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
from openerp import models, _


class ResPartnerBank(models.Model):
    """
    res.partner.bank recordset
    Add SQL constraint to avoid duplicates on acc_number field.
    """
    _inherit = 'res.partner.bank'

    _sql_constraints = [
        ('unique_bank_account', 'unique(acc_number)',
         _('Your account number already exist!')),
    ]
