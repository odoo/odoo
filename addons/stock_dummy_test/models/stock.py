# coding: utf-8
# #############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#    You should have received a copy of the GNU Affero General Public License
#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ##############################################################################

from openerp import models


class StockQuant(models.Model):

    _inherit = 'stock.quant'

    # pylint: disable=W0102
    def quants_get_prefered_domain(self, cr, uid, location, product, qty,
                                   domain=None, prefered_domain_list=[],
                                   restrict_lot_id=False,
                                   restrict_partner_id=False, context=None):
        """The original function tries to find quants in the given location for
        the given domain.
        This method is inherited to return specific quants if these are sending
        by context, if not the quant returned are the found for the original
        method.
        """
        res = context.get('force_quant', False) or \
            super(StockQuant, self).\
            quants_get_prefered_domain(
                cr, uid, location, product, qty, domain=domain,
                prefered_domain_list=prefered_domain_list,
                restrict_lot_id=restrict_lot_id,
                restrict_partner_id=restrict_partner_id, context=context)
        return res
