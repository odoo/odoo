import base64
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import freeze_time

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon


@freeze_time('2024-06-15')
@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtAtSeriesWS(TestL10nPtCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.at_public_cert = cls.env['certificate.certificate'].create({
            'name': 'AT Test Public Key',
            'content': cls._get_test_rsa_public_key_pem_b64(),
            'company_id': cls.company_pt.id,
        })
        cls.company_pt.write({
            'l10n_pt_at_ws_username': '599999999',
            'l10n_pt_at_ws_password': 'testpassword',
            'l10n_pt_at_ws_public_cert_id': cls.at_public_cert.id,
        })

    @staticmethod
    def _get_test_rsa_public_key_pem_b64():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return base64.b64encode(pem)

    def _mock_ws(self, return_code='ABC12345'):
        mock_ws = MagicMock()
        mock_ws.registar_serie.return_value = return_code
        return patch(
            'odoo.addons.l10n_pt_certification.utils.series_ws.L10nPtAtSeriesWS.registar_serie',
            return_value=return_code,
        )

    def test_action_register_at_series_sets_at_code(self):
        at_series = self.env['l10n_pt.at.series'].create({
            'name': '2025',
            'company_id': self.company_pt.id,
            'training_series': False,
            'date_start': '2025-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'FT',
        })
        self.assertFalse(at_series.at_code)

        with self._mock_ws('XYZ98765'):
            at_series.action_register_at_series()

        self.assertEqual(at_series.at_code, 'XYZ98765')

    def test_action_register_at_series_fault_raises_user_error(self):
        at_series = self.env['l10n_pt.at.series'].create({
            'name': '2025',
            'company_id': self.company_pt.id,
            'training_series': False,
            'date_start': '2025-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'FT',
        })

        def raise_fault(*args, **kwargs):
            raise UserError("AT Series registration failed.")

        with patch(
            'odoo.addons.l10n_pt_certification.utils.series_ws.L10nPtAtSeriesWS.registar_serie',
            side_effect=raise_fault,
        ):
            with self.assertRaises(UserError):
                at_series.action_register_at_series()

        self.assertFalse(at_series.at_code)

    def test_create_auto_registers_when_credentials_configured(self):
        with self._mock_ws('AUTO001') as mock:
            series = self.env['l10n_pt.at.series'].create({
                'name': '2025',
                'company_id': self.company_pt.id,
                'training_series': False,
                'date_start': '2025-01-01',
                'journal_id': self.company_data['default_journal_sale'].id,
                'document_type': 'out_invoice',
                'prefix': 'FT',
            })
            mock.assert_called_once()
            self.assertEqual(series.at_code, 'AUTO001')

    def test_create_does_not_block_on_ws_failure(self):
        def raise_fault(*args, **kwargs):
            raise UserError("Service unavailable")

        with patch(
            'odoo.addons.l10n_pt_certification.utils.series_ws.L10nPtAtSeriesWS.registar_serie',
            side_effect=raise_fault,
        ):
            series = self.env['l10n_pt.at.series'].create({
                'name': '2025',
                'company_id': self.company_pt.id,
                'training_series': False,
                'date_start': '2025-01-01',
                'journal_id': self.company_data['default_journal_sale'].id,
                'document_type': 'out_invoice',
                'prefix': 'FT',
            })

        self.assertTrue(series.exists())
        self.assertFalse(series.at_code)

    def test_create_skips_when_no_credentials(self):
        company_no_creds = self.env['res.company'].create({
            'name': 'No Creds Co',
        })
        with self._mock_ws() as mock:
            series = self.env['l10n_pt.at.series'].create({
                'name': '2025',
                'company_id': company_no_creds.id,
                'training_series': False,
                'date_start': '2025-01-01',
                'journal_id': self.company_data['default_journal_sale'].id,
                'document_type': 'out_invoice',
                'prefix': 'FT',
            })

        mock.assert_not_called()
        self.assertFalse(series.at_code)

    def test_create_skips_when_at_code_already_set(self):
        with self._mock_ws() as mock:
            series = self.env['l10n_pt.at.series'].create({
                'name': '2025',
                'company_id': self.company_pt.id,
                'training_series': False,
                'date_start': '2025-01-01',
                'journal_id': self.company_data['default_journal_sale'].id,
                'document_type': 'out_invoice',
                'prefix': 'FT',
                'at_code': 'MANUAL01',
            })

        mock.assert_not_called()
        self.assertEqual(series.at_code, 'MANUAL01')

    def test_document_type_mapping(self):
        from odoo.addons.l10n_pt_certification.const import PT_AT_DOCUMENT_TYPE_MAPPING

        at_series = self.env['l10n_pt.at.series'].create({
            'name': '2025',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2025-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'FT',
        })
        params = at_series._l10n_pt_at_ws_get_registration_params()
        self.assertEqual(params['classeDoc'], 'SI')
        self.assertEqual(params['tipoDoc'], 'FT')
        self.assertEqual(params['tipoSerie'], 'F')

        at_series.document_type = 'payment_receipt'
        at_series.training_series = False
        params = at_series._l10n_pt_at_ws_get_registration_params()
        self.assertEqual(params['classeDoc'], 'PY')
        self.assertEqual(params['tipoDoc'], 'RG')
        self.assertEqual(params['tipoSerie'], 'N')

    def test_action_register_requires_credentials(self):
        company_no_creds = self.env['res.company'].create({
            'name': 'No Creds Co',
        })
        at_series = self.env['l10n_pt.at.series'].create({
            'name': '2025',
            'company_id': company_no_creds.id,
            'training_series': False,
            'date_start': '2025-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'FT',
        })
        with self.assertRaises(UserError):
            at_series.action_register_at_series()
