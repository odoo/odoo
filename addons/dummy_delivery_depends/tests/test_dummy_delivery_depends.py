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

from openerp.addons.stock_dummy_test.tests import test_dummy_stock_test


class TestDummyStockWithDelivery(test_dummy_stock_test.TestDummyStockTest):

    def test_01_normal_moves_dummy_stock_test(self):
        """Test to verify the normal behavior for moves from different types of
        locations
        """
        # Creating first move between stock and customer locations
        move_brw2 = self.create_move(self.stock.id, self.customer.id,
                                    4)

        # Validating move
        move_brw2.action_done()
