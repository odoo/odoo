from odoo.fields import Command
from odoo.modules.module import get_module_path, load_script
from odoo.tests import common


class TestPostMigrate11(common.TransactionCase):
    """Tests for ``gamification/migrations/1.1/post-migrate.py``.

    The script is loaded through :func:`~odoo.modules.module.load_script`, the
    same loader Odoo uses, and run against the test cursor: unlike the SQL-only
    pre-migrate scripts elsewhere in the tree it drives the ORM, so a mocked
    cursor would test nothing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.script = load_script(
            f"{get_module_path('gamification')}/migrations/1.1/post-migrate.py",
            "gamification_1_1_post_migrate",
        )

    def test_post_migrate_leaves_the_converted_rows_alone(self):
        """base 1.97 turned the noupdate rules into ir.access rows: the script
        finds rows, not rules, and must neither fail nor rewrite them."""
        data = self.env["ir.model.data"].search(
            [("module", "=", "gamification"), ("model", "=", "ir.access")]
        )
        rows = self.env["ir.access"].browse(data.mapped("res_id"))
        before = {row: (row.group_id, row.operation, row.domain) for row in rows}

        self.script.migrate(self.env.cr, "19.0.1.0")

        self.assertEqual(
            {row: (row.group_id, row.operation, row.domain) for row in rows}, before
        )

    def test_post_migrate_cleans_root_menu_groups(self):
        """The root ends up on the app tier alone, with no base.group_no_one left.

        <menuitem groups="..."> emits Command.link, so on an existing database
        the old gate survives next to the new one and the tile stays invisible
        outside developer mode. Reproduced here by re-linking it.
        """
        root = self.env.ref("gamification.gamification_menu")
        app_group = self.env.ref("gamification.group_gamification_user")
        root.group_ids = [
            Command.set([self.env.ref("base.group_no_one").id, app_group.id])
        ]

        self.script.migrate(self.env.cr, "19.0.1.0")

        self.assertEqual(root.group_ids, app_group)
