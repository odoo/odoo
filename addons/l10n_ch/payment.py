# -*- encoding: utf-8 -*-
#
#  payment.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
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
"""Override of pament order for adding a get wizard function"""

from osv import osv

class PaymentOrder(osv.osv):
    """Override of pament order for adding a get wizard function"""
    _inherit = 'payment.order'
    def get_wizard(self, mode):
        "Return the good wizard in function of the payment type"
        if mode == 'opae':
            #return 'l10n_ch','wizard_account_opae_create'
            raise wizard.except_wizard(
                                _('Warning'),
                                _('Functionality is not yet stable'+
                                'please look at lp:openerp-swiss-localization'+
                                ' for latest version warning Beta version' )
                            )
        elif mode == 'dta':
            return 'l10n_ch','wizard_account_dta_create'
        else:
            return super(PaymentOrder, self).get_wizard(mode)
PaymentOrder()