from odoo.tests import TransactionCase, tagged

from odoo.addons.base.models.ir_access_convert import noupdate_shortfalls

MODULE = "test_shortfall"
MODEL = "res.partner.industry"


@tagged("post_install", "-at_install")
class TestNoupdateShortfalls(TransactionCase):
    # the shape sign's completed documents had on the production dump: the
    # managers' noupdate row converted without unlink, and the users' converted
    # access line carrying it, which the module's file no longer ships

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.access"].search([("model_id.model", "=", MODEL)]).active = False
        cls.shipped = {
            f"{MODULE}.manager": {
                "kind": "permission",
                "group": "base.group_system",
                "operation": "crud",
                "model": "base.model_res_partner_industry",
            }
        }

    def _row(self, name, operation, *, noupdate, group="base.group_system"):
        row = self.env["ir.access"].create(
            {
                "name": name,
                "model_id": self.env["ir.model"]._get_id(MODEL),
                "group_id": self.env.ref(group).id,
                "kind": "permission",
                "operation": operation,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": MODULE,
                "name": name,
                "model": "ir.access",
                "res_id": row.id,
                "noupdate": noupdate,
            }
        )
        self.env.flush_all()
        return row

    def test_an_operation_only_an_unshipped_row_carried_is_named(self):
        self._row("manager", "cru", noupdate=True)
        self._row("carrier", "d", noupdate=False, group="base.group_user")
        self.assertEqual(
            noupdate_shortfalls(self.env.cr, self.shipped, {MODULE}),
            [(f"{MODULE}.manager", MODEL, "d")],
        )

    def test_nothing_is_named_once_the_row_holds_its_file_s_operations(self):
        self._row("manager", "crud", noupdate=True)
        self._row("carrier", "d", noupdate=False, group="base.group_user")
        self.assertEqual(noupdate_shortfalls(self.env.cr, self.shipped, {MODULE}), [])

    def test_a_shipped_or_kept_row_granting_the_operation_is_enough(self):
        self._row("manager", "cru", noupdate=True)
        self._row("carrier", "d", noupdate=False, group="base.group_user")
        shipped = dict(
            self.shipped,
            **{
                f"{MODULE}.carrier": dict(
                    self.shipped[f"{MODULE}.manager"], operation="d"
                )
            },
        )
        self.assertEqual(noupdate_shortfalls(self.env.cr, shipped, {MODULE}), [])
        # a module outside the upgrade keeps its rows: nothing drops the carrier
        self.assertEqual(noupdate_shortfalls(self.env.cr, self.shipped, set()), [])
