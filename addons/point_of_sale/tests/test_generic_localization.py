from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import Form, tagged
from odoo.fields import Command


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericLocalization(TestPointOfSaleHttpCommon):
    allow_inherited_tests_method = True

    # Partner fields a localization needs in the POS "Edit/Create customer" form
    # (e.g. to invoice). Subclasses extend this with their mandatory l10n fields;
    # the test below materializes the actual view POS opens and asserts they are
    # present.
    pos_partner_pos_form_fields = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.name = "AAAA Generic Partner"
        cls.partner_a.vat = "32345678"
        cls.whiteboard_pen.sudo().write({
            'standard_price': 10.0,
            'taxes_id': [Command.link(cls.tax_sale_a.id)]
        })

        cls.wall_shelf.sudo().write({
            'standard_price': 10.0,
            'taxes_id': [Command.link(cls.tax_sale_a.id)]
        })

    def test_generic_localization(self):
        self.main_pos_config.open_ui()
        url = "/pos/ui?config_id=%d" % self.main_pos_config.id
        url += "&company_name=%s" % self.main_pos_config.company_id.name
        self.start_tour(url, "generic_localization_tour", login="accountman")
        last_order = self.main_pos_config.current_session_id.order_ids[-1]
        html_data = last_order.order_receipt_generate_html()
        last_order.order_receipt_generate_image()  # verify if image generation works
        return last_order, html_data

    def test_pos_partner_form_exposes_l10n_fields(self):
        """The POS "Edit/Create customer" view must render the localization's mandatory partner fields."""
        partner = self.env['res.partner']
        view_id = partner._get_pos_partner_view_id()
        form = Form(partner, view=view_id)
        for field_name in self.pos_partner_pos_form_fields:
            self.assertIn(
                field_name, form._view['fields'],
                f"{field_name!r} is missing from the POS partner form for this "
                f"localization (view id {view_id}); POS can no longer capture it.",
            )
