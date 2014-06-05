from mock import Mock

from openerp.tests.common import BaseCase
from openerp.osv.orm import browse_record
import openerp
from openerp.modules.registry import RegistryManager

DB = openerp.tools.config['db_name']


class TestGroupOrders(BaseCase):

    def setUp(self):
        super(TestGroupOrders, self).setUp()

        self.order1 = Mock()
        self.order2 = Mock()

        self.order1.order_line = self.order2.order_line = []
        self.order1.origin = self.order2.origin = ''
        self.order1.notes = self.order2.notes = ''

        # I have to use the registry to get an instance of a model. I cannot
        # use the class constructor because that is modified to return nothing.
        self.registry = RegistryManager.get(DB)
        self.po = self.registry('purchase.order')
        # we do not actually use the database
        self.cr = None
        self.uid = None

    def test_no_orders(self):
        """Group an empty list of orders as an empty dictionary."""

        grouped = self.po._group_orders(self.cr, self.uid, [])
        self.assertEquals(grouped, {})

    def test_one_order(self):
        """A single order will not be grouped."""
        grouped = self.po._group_orders(self.cr, self.uid, [self.order1])
        self.assertEquals(grouped, {})

    def test_two_similar_orders(self):
        """Two orders with the right conditions can be merged.

        We do not care about the order lines here.
        """
        self.order1.partner_id = self.order2.partner_id = Mock(
            spec=browse_record, id=1)
        self.order1.location_id = self.order2.location_id = Mock(
            spec=browse_record, id=2)
        self.order1.pricelist_id = self.order2.pricelist_id = Mock(
            spec=browse_record, id=3)

        self.order1.id = 51
        self.order2.id = 52

        grouped = self.po._group_orders(self.cr, self.uid,
                                        [self.order1, self.order2])
        expected_key = (('location_id', 2), ('partner_id', 1),
                        ('pricelist_id', 3))
        self.assertEquals(grouped.keys(), [expected_key])
        self.assertEquals(grouped[expected_key][1], [51, 52])

    def test_merge_origin_and_notes(self):
        self.order1.origin = 'ORIGIN1'
        self.order2.origin = 'ORIGIN2'

        self.order1.notes = 'Notes1'
        self.order2.notes = 'Notes2'

        self.order1.partner_id = self.order2.partner_id = Mock(
            spec=browse_record, id=1)
        self.order1.location_id = self.order2.location_id = Mock(
            spec=browse_record, id=2)
        self.order1.pricelist_id = self.order2.pricelist_id = Mock(
            spec=browse_record, id=3)

        grouped = self.po._group_orders(
            self.cr, self.uid, [self.order1, self.order2])

        expected_key = (('location_id', 2), ('partner_id', 1),
                        ('pricelist_id', 3))

        merged_data = grouped[expected_key][0]

        self.assertEquals(merged_data['origin'], 'ORIGIN1 ORIGIN2')
        self.assertEquals(merged_data['notes'], 'Notes1\nNotes2')
