from odoo.tests.common import TransactionCase


class TestDatetimeExtract(TransactionCase):

    def test_100_translit_ua_mixin(self):
        translitua = self.env['kw.translit.ua.mixin'].translitua

        self.assertEqual(translitua('ЗГУРОВСЬКИЙ'), 'ZGHUROVS\'KYI')
        self.assertEqual(
            translitua('ЗГУРОВСЬКИЙ', preserve_case=False), 'ZGhUROVS\'KYI')
