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

    def test_the_batch_form_shows_the_responsible_as_an_avatar(self):
        arch = self._arch("stock_picking_batch.stock_picking_batch_form", "form")
        nodes = arch.xpath('//field[@name="user_id"]')
        self.assertTrue(nodes, "the batch form declares no user_id field at all")
        self.assertEqual(
            nodes[0].get("widget"),
            "many2one_avatar_user",
            "the list and the kanban of this same view file already show the "
            "responsible as an avatar; the form was the only one left as text",
        )

    def test_the_wave_action_opens_a_form_that_cannot_create(self):
        action = self.env.ref("stock_picking_batch.action_picking_tree_wave")
        views = {view.view_mode: view.view_id for view in action.view_ids}
        self.assertEqual(set(views), {"list", "kanban", "form"})
        for view_type, view in views.items():
            arch = self._arch(view.get_external_id()[view.id], view_type)
            self.assertEqual(
                arch.get("create"),
                "0",
                f"the wave {view_type} must not create: a record made there is a "
                "batch (is_wave is not set) that the wave action's domain hides",
            )
        batch_form = self._arch("stock_picking_batch.stock_picking_batch_form", "form")
        self.assertNotEqual(batch_form.get("create"), "0")
