from odoo.exceptions import AccessError
from odoo.tests import users, tagged
from .common import MassMailCommon


@tagged('mass_mailing')
class TestMassMailingSnippets(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_snippet, cls.blocking_snippet = cls.env['ir.ui.view'].create([{
            'name': "Custom snippet",
            'key': "mass_mailing.custom_snippet",
            'type': 'qweb',
            'arch': "<section>Coucou</section>",
            'technical_usage': "mass_mailing",
        }, {
            'name': "Custom Blocking snippet",
            'key': "mass_mailing.blocking_snippet",
            'type': 'qweb',
            'arch': "<section>Shouldn't work</section>",
            }
        ])

    @users("user_marketing")
    def test_mailing_custom_snippets_features(self):
        IrUiView = self.env['ir.ui.view']
        for tested_view in [self.blocking_snippet, self.original_snippet]:
            with self.subTest(tested_view=tested_view.key):
                view_id, key = tested_view.mapped(lambda view: [view.id, view.key])[0]
                if tested_view.technical_usage:
                    IrUiView.rename_snippet("My original Name", view_id, key)
                    self.assertEqual(tested_view.name, "My original Name")
                    IrUiView.delete_snippet(view_id, key)
                else:
                    with self.assertRaises(AccessError):
                        IrUiView.delete_snippet(view_id, key)
                    with self.assertRaises(AccessError):
                        IrUiView.rename_snippet("some original name", view_id, key)
        saved_name = IrUiView.save_snippet("My custom Snippet", "<section>Should Work</section>", "mass_mailing.email_designer_snippets", "custom_snippet_working", "https://www.example.com", "mass_mailing")
        saved_view = IrUiView.search([("name", "=", saved_name)])
        value = IrUiView.render_public_asset("mass_mailing.email_designer_snippets")
        data_snippet = saved_view.key.split(".")[1]
        self.assertIn(f'data-snippet="{data_snippet}"', str(value))
