from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestVerifactuPartnerIdTypes(TransactionCase):
    """ Wiring check: Veri*factu builds its IDDestinatario via `_l10n_es_edi_verifactu_get_values`,
    which just wraps the shared `_l10n_es_edi_get_partner_info` (also used by SII). The full ID-type
    priority matrix is covered there (l10n_es/tests/test_res_partner.py); here we only prove the
    wiring is intact end to end. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'VF Foreign Partner (Passport)',
            'country_id': cls.env.ref('base.us').id,
            'l10n_es_passport': 'X1234567',
        })

    def test_verifactu_values_include_name_and_id_otro(self):
        values = self.partner._l10n_es_edi_verifactu_get_values()
        self.assertEqual(values['NombreRazon'], 'VF Foreign Partner (Passport)')
        self.assertEqual(values['IDOtro'], {
            'IDType': '03',
            'ID': 'X1234567',
            'CodigoPais': 'US',
        })
