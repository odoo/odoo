# -*- encoding: utf-8 -*-
#  account_move_line.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields, osv

class AccountMoveLine(osv.osv):
    """ Inherit account.move.line in order to add a custom link 
        between supplier invoice line and bank. The original link 
        was defined in account_payment between line """

    _inherit = 'account.move.line'

    ## @param self The object pointer.
    ## @param cursor a psycopg cursor
    ## @param uid res.user.id that is currently loged
    ## @param payment_type manual 
    ## @parma context a standard dict 
    ## @return a dict  who has the account 
    #  move line id as key and the bank id as value
    def line2bank(self, cursor, uid, ids, payment_type='manual', context=None):
        """add a link to account.move.line in order to link 
        supplier invoice line and bank. The original link 
        was defined in account_payment"""
        payment_mode_obj = self.pool.get('payment.mode')
        line2bank = {}
        if not ids:
            return {}
        bank_type = payment_mode_obj.suitable_bank_types(cursor, uid, payment_type,
                context=context)
        for line in self.browse(cursor, uid, ids, context=context):
            if line.invoice and line.invoice.partner_bank:
                line2bank[line.id] = line.invoice.partner_bank.id
            elif line.partner_id:
                for bank in line.partner_id.bank_ids:
                    if bank.state in bank_type:
                        line2bank[line.id] = bank.id
                        break
                if line.id not in line2bank and line.partner_id.bank_ids:
                    line2bank[line.id] = line.partner_id.bank_ids[0].id
        return line2bank

AccountMoveLine()
