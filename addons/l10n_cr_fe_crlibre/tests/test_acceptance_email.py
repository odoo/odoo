from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAcceptanceEmail(TransactionCase):

    def setUp(self):
        super().setUp()
        partner = self.env['res.partner'].create({'name': 'Cliente Demo', 'email': 'cliente@demo.cr'})
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id,
            'l10n_cr_fe_clave': '5' * 50,
            'l10n_cr_fe_xml_firmado': '<FacturaElectronica>firmada</FacturaElectronica>',
            'l10n_cr_fe_respuesta_xml': '<MensajeHacienda>aceptado</MensajeHacienda>',
        })

    def test_send_acceptance_email_attaches_both_xmls(self):
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail') as m_send:
            self.invoice._l10n_cr_fe_send_acceptance_email()
        m_send.assert_called_once()
        attachment_ids = m_send.call_args.kwargs['email_values']['attachment_ids'][0][2]
        self.assertEqual(len(attachment_ids), 2)

    def test_send_acceptance_email_skips_without_partner_email(self):
        self.invoice.partner_id.email = False
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail') as m_send:
            self.invoice._l10n_cr_fe_send_acceptance_email()
        m_send.assert_not_called()
