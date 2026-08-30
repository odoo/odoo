from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "accruals")
class TestAccrualLevelExport(HttpCase):
    """The import-compatible export drops every field the ORM reports readonly.

    ``addons/web/controllers/export.py`` skips them so that the resulting file
    can be fed back through the importer, and ``odoo/orm/fields/base.py`` marks
    any computed field without an inverse readonly by default.  A computed field
    the user *does* edit therefore has to say ``readonly=False`` or it silently
    disappears from the export, and re-importing an accrual plan loses it.
    """

    def _import_compatible_field_names(self, model):
        self.authenticate("admin", "admin")
        result = self.make_jsonrpc_request(
            "/web/export/get_fields",
            {"model": model, "domain": [], "import_compat": True},
        )
        return {field["id"] for field in result}

    def test_user_editable_accrual_level_fields_are_exportable(self):
        field_names = self._import_compatible_field_names("hr.leave.accrual.level")

        # These three carry the same shape -- a compute that only forces a value
        # in one situation, and a form widget the user drives the rest of the
        # time -- so they have to travel together through an export/import round
        # trip.  Losing only one of them reimports a plan that silently disagrees
        # with the one it came from.
        self.assertIn("action_with_unused_accruals", field_names)
        self.assertIn("carryover_options", field_names)
        self.assertIn("accrual_validity", field_names)
