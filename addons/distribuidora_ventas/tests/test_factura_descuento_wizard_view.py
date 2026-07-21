import re

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFacturaDescuentoWizardView(TransactionCase):

    def test_discount_button_present_and_points_to_wizard_action(self):
        action = self.env.ref('distribuidora_ventas.action_factura_descuento_wizard')
        view = self.env['account.move'].get_view(view_type='form')
        match = re.search(r'<button[^>]*string="Descuento general"[^>]*/>', view['arch'])
        self.assertIsNotNone(match, "no se encontro el boton 'Descuento general' en la vista combinada")
        self.assertIn(f'name="{action.id}"', match.group(0))

    def test_discount_field_shown_by_default_on_invoice_lines(self):
        view = self.env['account.move'].get_view(view_type='form')
        match = re.search(r'<field[^>]*name="discount"[^>]*width="50px"[^>]*/>', view['arch'])
        self.assertIsNotNone(match, "no se encontro el campo discount (ancho 50px) en la vista combinada")
        self.assertIn('optional="show"', match.group(0))
