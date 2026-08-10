from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCabysWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Frutas Demo Test SA'})
        self.env['account.chart.template'].try_loading('generic_coa', company=self.company)
        self.env.user.company_id = self.company
        self.product = self.env['product.template'].create({'name': 'Aguacate Hass'})

    def _patch_buscar(self, resultados):
        return patch(
            'odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.CabysClient.buscar',
            return_value=resultados)

    def test_action_buscar_llena_result_ids(self):
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'aguacate',
        })
        resultados = [
            {'codigo': '0131100020400', 'descripcion': 'Aguacate haas, fresco', 'impuesto': 1.0},
            {'codigo': '0131100020100', 'descripcion': 'Aguacate, otro tipo', 'impuesto': 13.0},
        ]
        with self._patch_buscar(resultados):
            wizard.action_buscar()
        self.assertTrue(wizard.searched)
        self.assertEqual(len(wizard.result_ids), 2)
        self.assertEqual(wizard.result_ids[0].codigo, '0131100020400')
        self.assertEqual(wizard.result_ids[0].impuesto, 1.0)

    def test_action_buscar_sin_resultados_deja_searched_true(self):
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'xyzxyzxyz',
        })
        with self._patch_buscar([]):
            wizard.action_buscar()
        self.assertTrue(wizard.searched)
        self.assertEqual(len(wizard.result_ids), 0)

    def test_action_buscar_repetido_reemplaza_resultados_anteriores(self):
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'aguacate',
        })
        with self._patch_buscar([{'codigo': '0131100020400', 'descripcion': 'x', 'impuesto': 1.0}]):
            wizard.action_buscar()
        with self._patch_buscar([{'codigo': '0131100020100', 'descripcion': 'y', 'impuesto': 13.0}]):
            wizard.action_buscar()
        self.assertEqual(len(wizard.result_ids), 1)
        self.assertEqual(wizard.result_ids[0].codigo, '0131100020100')

    def test_action_buscar_propaga_error_de_red_como_usererror(self):
        from odoo.exceptions import UserError

        from odoo.addons.l10n_cr_fe_crlibre.models.cabys_client import CabysApiError

        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({
            'product_id': self.product.id, 'query': 'aguacate',
        })
        with patch(
            'odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.CabysClient.buscar',
            side_effect=CabysApiError("No se pudo conectar con la API de Hacienda: timeout"),
        ):
            with self.assertRaises(UserError):
                wizard.action_buscar()
        self.assertFalse(wizard.searched)

    def test_action_usar_con_impuesto_configurado_asigna_todo(self):
        tax = self.env['account.tax'].create({
            'name': 'IVA 1%', 'amount_type': 'percent', 'amount': 1.0,
            'type_tax_use': 'sale', 'company_id': self.company.id,
        })
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({'product_id': self.product.id})
        line = self.env['l10n_cr.fe.cabys.wizard.line'].create({
            'wizard_id': wizard.id, 'codigo': '0131100020400',
            'descripcion': 'Aguacate haas, fresco', 'impuesto': 1.0,
        })
        result = line.action_usar()
        self.assertEqual(result, {'type': 'ir.actions.act_window_close'})
        self.assertEqual(self.product.l10n_cr_fe_cabys, '0131100020400')
        self.assertEqual(self.product.l10n_cr_fe_cabys_descripcion, 'Aguacate haas, fresco')
        self.assertEqual(self.product.taxes_id, tax)

    def test_action_usar_sin_impuesto_configurado_no_lo_toca(self):
        original_taxes = self.product.taxes_id
        wizard = self.env['l10n_cr.fe.cabys.wizard'].create({'product_id': self.product.id})
        line = self.env['l10n_cr.fe.cabys.wizard.line'].create({
            'wizard_id': wizard.id, 'codigo': '0131100020400',
            'descripcion': 'Aguacate haas, fresco', 'impuesto': 1.0,
        })
        line.action_usar()
        self.assertEqual(self.product.l10n_cr_fe_cabys, '0131100020400')
        self.assertEqual(self.product.taxes_id, original_taxes)
        self.assertTrue(any(
            'no existe un impuesto de venta' in (msg.body or '')
            for msg in self.product.message_ids))
