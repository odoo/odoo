from odoo.exceptions import AccessError
from odoo.tests import users, tagged
from .common import MassMailCommon


@tagged('mass_mailing')
class TestMassMailingSnippets(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_snippet, cls.blocking_snippet = cls.env['ir.qweb'].create([{
            'name': "Custom snippet",
            'key': "mass_mailing.custom_snippet",
            'arch': "<section>Coucou</section>",
            'technical_usage': "mass_mailing",
        }, {
            'name': "Custom Blocking snippet",
            'key': "mass_mailing.blocking_snippet",
            'arch': "<section>Shouldn't work</section>",
            }
        ])

    @users("user_marketing")
    def test_mailing_custom_snippets_features(self):
        IrQweb = self.env['ir.qweb']
        for tested_view in [self.blocking_snippet, self.original_snippet]:
            with self.subTest(tested_view=tested_view.key):
                view_id, key = tested_view.mapped(lambda view: [view.id, view.key])[0]
                if tested_view.technical_usage:
                    IrQweb.rename_snippet("My original Name", view_id, key)
                    self.assertEqual(tested_view.name, "My original Name")
                    IrQweb.delete_snippet(view_id, key)
                else:
                    with self.assertRaises(AccessError):
                        IrQweb.delete_snippet(view_id, key)
                    with self.assertRaises(AccessError):
                        IrQweb.rename_snippet("some original name", view_id, key)
        saved_name = IrQweb.save_snippet("My custom Snippet", "<section>Should Work</section>", "mass_mailing.email_designer_snippets", "custom_snippet_working", "https://www.example.com", "mass_mailing")
        saved_view = IrQweb.search([("name", "=", saved_name)])
        value = IrQweb.render_public_asset("mass_mailing.email_designer_snippets")
        data_snippet = saved_view.key.split(".")[1]
        self.assertIn(f'data-snippet="{data_snippet}"', str(value))
