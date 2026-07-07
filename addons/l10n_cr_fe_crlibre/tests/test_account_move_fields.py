from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountMoveFeFields(TransactionCase):

    def test_new_fe_fields_exist_with_defaults(self):
        partner = self.env['res.partner'].create({'name': 'Cliente FE Fields'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
        })
        self.assertEqual(invoice.l10n_cr_fe_state, 'draft')
        self.assertFalse(invoice.l10n_cr_fe_xml_firmado)
        self.assertFalse(invoice.l10n_cr_fe_respuesta_xml)
        self.assertFalse(invoice.l10n_cr_fe_motivo_rechazo)

    def test_state_selection_includes_all_expected_values(self):
        field = self.env['account.move']._fields['l10n_cr_fe_state']
        keys = [key for key, _label in field.selection]
        self.assertEqual(
            keys, ['draft', 'generado', 'enviado', 'aceptado', 'rechazado', 'error'])
