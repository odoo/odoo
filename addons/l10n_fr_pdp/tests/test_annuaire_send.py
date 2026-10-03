from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAnnuaireSend(TestL10nFrPdpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.account_peppol_proxy_state = 'receiver'

    def _create_not_in_annuaire_partner(self):
        return self.env['res.partner'].create({
            'name': 'Buyer Not In Annuaire',
            'street': '1 rue Test',
            'zip': '75001',
            'city': 'Paris',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
            'siret': '33341752200018',
            'invoice_edi_format': 'ubl_21_fr',
            'peppol_eas': '0225',
            'peppol_endpoint': '111111111',
        })

    def test_partner_not_in_annuaire_indicator(self):
        partner = self._create_not_in_annuaire_partner()
        partner.button_account_peppol_check_partner_endpoint()
        self.assertEqual(partner.peppol_verification_state, 'not_valid')
        self.assertTrue(partner.l10n_fr_pdp_not_in_annuaire)

    def test_send_wizard_force_unlocks_peppol(self):
        partner = self._create_not_in_annuaire_partner()
        move = self._create_french_invoice(partner_id=partner.id)
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertTrue(wizard.sending_method_checkboxes['peppol']['readonly'])
        wizard.l10n_fr_pdp_force_send_einvoicing = True
        wizard._onchange_l10n_fr_pdp_force_send_einvoicing()
        self.assertFalse(wizard.sending_method_checkboxes['peppol']['readonly'])
        self.assertTrue(wizard.sending_method_checkboxes['peppol']['checked'])
        self.assertEqual(partner.peppol_verification_state, 'not_valid')

    @patch('odoo.addons.account_peppol.models.account_move_send.AccountMoveSend._send_peppol_documents')
    def test_send_wizard_force_allows_send(self, mock_send_peppol):
        partner = self._create_not_in_annuaire_partner()
        move = self._create_french_invoice(partner_id=partner.id)
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
            'l10n_fr_pdp_force_send_einvoicing': True,
        })
        wizard._onchange_l10n_fr_pdp_force_send_einvoicing()
        wizard.action_send_and_print()
        mock_send_peppol.assert_called()
        self.assertEqual(partner.peppol_verification_state, 'not_valid')

    def test_send_wizard_without_force_raises(self):
        partner = self._create_not_in_annuaire_partner()
        move = self._create_french_invoice(partner_id=partner.id)
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
            'sending_methods': ['peppol'],
        })
        with self.assertRaises(UserError):
            wizard.action_send_and_print()

    def test_batch_wizard_lists_not_in_annuaire_partners(self):
        partner = self._create_not_in_annuaire_partner()
        move = self._create_french_invoice(partner_id=partner.id)
        move.action_post()
        wizard = self.env['account.move.send.batch.wizard'].create({
            'move_ids': [(6, 0, move.ids)],
        })
        self.assertIn(partner, wizard.l10n_fr_pdp_not_in_annuaire_partner_ids)

    def test_is_applicable_to_move_with_force(self):
        partner = self._create_not_in_annuaire_partner()
        partner.button_account_peppol_check_partner_endpoint()
        move = self._create_french_invoice(partner_id=partner.id)
        move.action_post()
        send = self.env['account.move.send']
        settings = send._get_default_sending_settings(move)
        self.assertFalse(send._is_applicable_to_move('peppol', move, **settings))
        self.assertTrue(
            send.with_context(l10n_fr_pdp_force_send_einvoicing=True)._is_applicable_to_move(
                'peppol', move, **settings,
            )
        )
