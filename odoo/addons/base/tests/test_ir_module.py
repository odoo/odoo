from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase
from odoo.modules.module import Manifest
from odoo.tools import mute_logger


@tagged('at_install', '-post_install')  # LEGACY at_install
class IrModuleCase(TransactionCase):
    @mute_logger("odoo.modules.module")
    def test_missing_module_icon(self):
        module = self.env["ir.module.module"].create({"name": "missing"})
        base = self.env["ir.module.module"].search([("name", "=", "base")])
        self.assertEqual(base.icon_image.content, module.icon_image.content)

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

    def test_activate_lang_keeps_en_us_of_uninstalled_modules(self):
        """ Activating a language must not overwrite the en_US terms of uninstalled modules. """
        Module = self.env['ir.module.module']
        lang_code = 'fr_FR'
        module = source_name = None
        for candidate in Module.search([('state', '!=', 'installed')]):
            manifest = Manifest.for_addon(candidate.name, display_warning=False)
            if not manifest:
                continue
            translated = (manifest.get_translations([lang_code]).get('shortdesc') or {}).get(lang_code)
            name = Module.get_values_from_terp(manifest)['shortdesc']
            if translated and translated != name:
                module, source_name = candidate, name
                break
        if not module:
            self.skipTest("no uninstalled module with a translated name to check")

        lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', lang_code)])
        lang.active = True
        # en_US only becomes inactive once nothing refers to it anymore
        self.env['res.users'].with_context(active_test=False).search([]).lang = lang_code
        self.env['res.partner'].with_context(active_test=False).search([('lang', '=', 'en_US')]).lang = lang_code
        self.env.ref('base.lang_en').active = False

        Module._load_non_installed_modules_manifest_terms([lang_code])

        self.assertEqual(module.with_context(lang='en_US').shortdesc, source_name)


@tagged('at_install', '-post_install')
class TestModuleCategory(TransactionCase):

    def test_parent_circular_dependencies(self):
        Cats = self.env['ir.module.category']

        def create(name, **kw):
            return Cats.create(dict(kw, name=name))

        category_a = create('A', parent_id=False)
        category_b = create('B', parent_id=category_a.id)
        category_c = create('C', parent_id=category_b.id)

        with self.assertRaises(ValidationError):
            category_a.write({'parent_id': category_c.id})
        with self.assertRaises(ValidationError):
            category_b.write({'parent_id': category_b.id})
