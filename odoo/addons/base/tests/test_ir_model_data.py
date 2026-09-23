from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestUpdateXmlidsCacheDiscipline(TransactionCase):
    def _rollback_over(self, savepoint_body):
        self.env.cr.execute("SAVEPOINT test_xmlid_cache")
        try:
            savepoint_body()
            self.env.flush_all()
        finally:
            self.env.cr.execute("ROLLBACK TO SAVEPOINT test_xmlid_cache")
            self.env.cr.execute("RELEASE SAVEPOINT test_xmlid_cache")
            self.env.invalidate_all()

    def test_a_rolled_back_insert_leaves_no_cached_xmlid(self):
        imd = self.env["ir.model.data"]

        def body():
            record = self.env["res.partner"].create({"name": "probe"})
            imd._update_xmlids([{"xml_id": "test_xmlid_cache.probe", "record": record}])

        self._rollback_over(body)
        with self.assertRaises(
            ValueError,
            msg="the row is rolled back, so a lookup answering anything but "
            "'not found' is serving a cache entry no rollback could remove",
        ):
            imd._get_xmlid_target("test_xmlid_cache.probe")

    def test_a_rolled_back_repoint_does_not_keep_the_new_target(self):
        imd = self.env["ir.model.data"]
        first = self.env["res.partner"].create({"name": "first"})
        imd._update_xmlids([{"xml_id": "test_xmlid_cache.moved", "record": first}])
        self.assertEqual(
            imd._get_xmlid_target("test_xmlid_cache.moved"), ("res.partner", first.id)
        )

        def body():
            second = self.env["res.partner"].create({"name": "second"})
            imd._update_xmlids([{"xml_id": "test_xmlid_cache.moved", "record": second}])

        self._rollback_over(body)
        self.assertEqual(
            imd._get_xmlid_target("test_xmlid_cache.moved"),
            ("res.partner", first.id),
            "the repoint is rolled back, so the lookup must answer the "
            "surviving target, not a value seeded during the dead savepoint",
        )

    def test_a_repoint_is_visible_in_its_own_transaction(self):
        imd = self.env["ir.model.data"]
        first = self.env["res.partner"].create({"name": "first"})
        second = self.env["res.partner"].create({"name": "second"})
        imd._update_xmlids([{"xml_id": "test_xmlid_cache.live", "record": first}])
        self.assertEqual(
            imd._get_xmlid_target("test_xmlid_cache.live"), ("res.partner", first.id)
        )

        imd._update_xmlids([{"xml_id": "test_xmlid_cache.live", "record": second}])
        self.assertEqual(
            imd._get_xmlid_target("test_xmlid_cache.live"),
            ("res.partner", second.id),
            "without the cache seed, the repoint must still invalidate the "
            "cached old target for its own transaction",
        )

    def test_a_pure_insert_does_not_invalidate_the_default_cache(self):
        imd = self.env["ir.model.data"]
        record = self.env["res.partner"].create({"name": "fresh"})
        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            imd._update_xmlids([{"xml_id": "test_xmlid_cache.fresh", "record": record}])
        self.assertNotIn(
            (),
            [call.args for call in mock_clear.call_args_list],
            "a fresh xmlid can be cached by nobody, so inserting it must not "
            "cost every worker its default cache",
        )
        self.assertEqual(
            imd._get_xmlid_target("test_xmlid_cache.fresh"), ("res.partner", record.id)
        )


@tagged("post_install", "-at_install")
class TestIrModelDataCacheInvalidation(TransactionCase):
    def test_write_on_existing_groups_xmlid_clears_groups_cache(self):
        group = self.env.ref("base.group_user")
        imd = self.env["ir.model.data"].search(
            [("model", "=", "res.groups"), ("res_id", "=", group.id)], limit=1
        )
        self.assertTrue(imd, "expected an ir.model.data row for base.group_user")

        with patch.object(
            self.env.registry,
            "clear_cache",
            wraps=self.env.registry.clear_cache,
        ) as mock_clear:
            imd.write({"noupdate": True})

        cleared = [call.args for call in mock_clear.call_args_list]
        self.assertIn(
            ("groups",),
            cleared,
            "writing a res.groups xmlid must invalidate the `groups` cache even "
            "when vals does not include `model`",
        )

    def test_unlinking_a_record_xmlid_invalidates_only_xmlids(self):
        record = self.env["res.partner"].create({"name": "exported"})
        imd = self.env["ir.model.data"].create(
            {
                "module": "__export__",
                "name": "exported_partner",
                "model": "res.partner",
                "res_id": record.id,
            }
        )
        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            imd.unlink()
        self.assertEqual(
            [call.args for call in mock_clear.call_args_list], [("xmlid",)]
        )

    def test_unlinking_a_menu_xmlid_leaves_no_stale_loaded_menu(self):
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Xmlid probe",
                "action": f"ir.actions.act_window,{self.env.ref('base.action_res_users').id}",
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "__test__",
                "name": "xmlid_probe_menu",
                "model": "ir.ui.menu",
                "res_id": menu.id,
            }
        )
        Menu = self.env["ir.ui.menu"]
        self.assertEqual(
            Menu.load_menus(False)[menu.id]["xmlid"], "__test__.xmlid_probe_menu"
        )
        self.env["ir.model.data"].search(
            [("model", "=", "ir.ui.menu"), ("res_id", "=", menu.id)]
        ).unlink()
        self.assertEqual(Menu.load_menus(False)[menu.id]["xmlid"], "")
