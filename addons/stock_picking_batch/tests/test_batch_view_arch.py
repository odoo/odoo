from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBatchViewArch(TransactionCase):
    def _arch(self, xmlid, view_type):
        view = self.env.ref(xmlid)
        return etree.fromstring(
            self.env["stock.picking.batch"].get_view(view.id, view_type)["arch"]
        )

    def test_batches_can_be_searched_by_their_description(self):
        arch = self._arch("stock_picking_batch.stock_picking_batch_filter", "search")
        self.assertTrue(
            arch.xpath('//search/field[@name="description"]'),
            "the default batch search must offer description: an auto-created "
            "batch or wave carries its grouping criteria there and nowhere else",
        )

    def test_the_searched_description_is_a_real_stored_field(self):
        arch = self._arch("stock_picking_batch.stock_picking_batch_filter", "search")
        names = arch.xpath('//search/field[@name="description"]/@name')
        self.assertEqual(names, ["description"])
        field = self.env["stock.picking.batch"]._fields["description"]
        self.assertTrue(field.store, "an unstored field would make the ilike useless")
