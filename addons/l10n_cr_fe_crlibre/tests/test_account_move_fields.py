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

    def test_nota_credito_fields_exist_with_defaults(self):
        partner = self.env['res.partner'].create({'name': 'Cliente NC Fields'})
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': partner.id,
        })
        self.assertFalse(credit_note.l10n_cr_fe_fecha_emision)
        self.assertFalse(credit_note.l10n_cr_fe_motivo)
        self.assertFalse(credit_note.l10n_cr_fe_codigo_referencia)
        self.assertFalse(credit_note.l10n_cr_fe_razon)

    def test_motivo_selection_maps_to_expected_codigo_referencia(self):
        from odoo.addons.l10n_cr_fe_crlibre.models.account_move import L10N_CR_FE_MOTIVO_CODIGO_MAP
        self.assertEqual(L10N_CR_FE_MOTIVO_CODIGO_MAP, {
            'anulacion_total': '01',
            'correccion_monto': '02',
            'devolucion_mercancia': '06',
            'referencia_otro_documento': '04',
            'otros': '99',
        })

    def test_tipo_documento_map_has_fe_and_nc(self):
        from odoo.addons.l10n_cr_fe_crlibre.models.account_move import L10N_CR_FE_TIPO_DOCUMENTO
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO['out_invoice']['clave'], 'FE')
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO['out_invoice']['consecutivo_codigo'], '01')
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO['out_invoice']['gen_xml_action'], 'gen_xml_fe')
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO['out_refund']['clave'], 'NC')
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO['out_refund']['consecutivo_codigo'], '03')
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO['out_refund']['gen_xml_action'], 'gen_xml_nc')

    def test_es_tiquete_field_defaults_false(self):
        partner = self.env['res.partner'].create({'name': 'Cliente Tiquete Fields'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
        })
        self.assertFalse(invoice.l10n_cr_fe_es_tiquete)

    def test_tipo_documento_te_constant(self):
        from odoo.addons.l10n_cr_fe_crlibre.models.account_move import L10N_CR_FE_TIPO_DOCUMENTO_TE
        self.assertEqual(L10N_CR_FE_TIPO_DOCUMENTO_TE, {
            'clave': 'TE', 'consecutivo_codigo': '04', 'gen_xml_action': 'gen_xml_te',
        })
