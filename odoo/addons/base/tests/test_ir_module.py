from odoo.tests.common import tagged, TransactionCase
from odoo.tools import mute_logger


@tagged('at_install', '-post_install')  # LEGACY at_install
class IrModuleCase(TransactionCase):
    @mute_logger("odoo.modules.module")
    def test_missing_module_icon(self):
        module = self.env["ir.module.module"].create({"name": "missing"})
        base = self.env["ir.module.module"].search([("name", "=", "base")])
        self.assertEqual(base.icon_image, module.icon_image)

    @mute_logger("odoo.modules.module")
    def test_new_module_icon(self):
        module = self.env["ir.module.module"].new({"name": "missing"})
        self.assertFalse(module.icon_image)

    @mute_logger("odoo.modules.module")
    def test_module_wrong_icon(self):
        module = self.env["ir.module.module"].create(
            {"name": "wrong_icon", "icon": "/not/valid.png"}
        )
        self.assertFalse(module.icon_image)

    @mute_logger("odoo.modules.module")
    def test_falsy_res_id(self):
        module = self.env["ir.module.module"].create(
            {"name": "get_views_test", "state": "installed"},
        )
        report = self.env['ir.actions.report'].create({
            'name': 'good_data_report',
            'report_name': 'web_studio.test_duplicate_foo',
            'model': 'res.users',
        })
        self.env["ir.model.data"].create({
            "module": "get_views_test",
            "name": "bad_data",
            "model": "ir.actions.report",
            "res_id": 0,
        })
        self.env["ir.model.data"].create({
            "module": "get_views_test",
            "name": "good_data",
            "model": "ir.actions.report",
            "res_id": report.id,
        })
        self.assertEqual(module.reports_by_module, "good_data_report")
        self.assertEqual(module.state, "installed")
        module.module_uninstall()
        self.assertEqual(module.state, "uninstalled")
