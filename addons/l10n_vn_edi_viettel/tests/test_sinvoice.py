from unittest.mock import patch
from odoo.tests import tagged, TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSInvoiceSymbol(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vietnam = cls.env.ref('base.vn')

        cls.company_vn_1 = cls.env['res.company'].create({
            'name': 'VN Company A',
            'country_id': cls.vietnam.id,
            'vat': '0123456789',
        })
        cls.company_vn_2 = cls.env['res.company'].create({
            'name': 'VN Company B',
            'country_id': cls.vietnam.id,
            'vat': '9876543210',
        })
        cls.company_us = cls.env['res.company'].create({
            'name': 'US Company',
            'country_id': cls.env.ref('base.us').id,
            'vat': '111222333',
        })

    def _mock_api_fetch_symbols(self, symbols):
        """Helper to build a mock API response."""
        return {'template': [{'invoiceSeri': code, 'templateCode': name} for code, name in symbols]}, None

    def test_fetch_symbols_creates_new_symbols(self):
        """Fetching symbols from the API should create new symbol records."""
        request_response = self._mock_api_fetch_symbols([('C23TSA', '1/001'), ('C23TSB', '1/002')])
        with patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice.L10n_Vn_Edi_ViettelSinvoiceSymbol._l10n_vn_edi_lookup_symbols', return_value=request_response):
            self.env['l10n_vn_edi_viettel.sinvoice.symbol'].with_company(self.company_vn_1).action_fetch_symbols()

        symbols = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].search([('company_id', '=', self.company_vn_1.id)])
        self.assertEqual(len(symbols), 2)
        self.assertRecordValues(symbols, [
            {'name': 'C23TSA', 'invoice_template_code': '1/001', 'company_id': self.company_vn_1.id},
            {'name': 'C23TSB', 'invoice_template_code': '1/002', 'company_id': self.company_vn_1.id},
        ])

    def test_fetch_symbols_no_duplicates_on_refetch(self):
        """Fetching the same symbols multiple times should not create duplicates."""
        request_response = self._mock_api_fetch_symbols([('C23TSA', '1/001')])
        with patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice.L10n_Vn_Edi_ViettelSinvoiceSymbol._l10n_vn_edi_lookup_symbols', return_value=request_response):
            self.env['l10n_vn_edi_viettel.sinvoice.symbol'].with_company(self.company_vn_1).action_fetch_symbols()
            self.env['l10n_vn_edi_viettel.sinvoice.symbol'].with_company(self.company_vn_1).action_fetch_symbols()

        symbols = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].search([('company_id', '=', self.company_vn_1.id)])
        self.assertEqual(len(symbols), 1)

    def test_fetch_symbols_archives_removed_symbols(self):
        """Symbols no longer returned by the API should be archived."""
        request_response = self._mock_api_fetch_symbols([('C23TSA', '1/001'), ('C23TSB', '1/002')])
        with patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice.L10n_Vn_Edi_ViettelSinvoiceSymbol._l10n_vn_edi_lookup_symbols', return_value=request_response):
            self.env['l10n_vn_edi_viettel.sinvoice.symbol'].with_company(self.company_vn_1).action_fetch_symbols()

        request_response = self._mock_api_fetch_symbols([('C23TSA', '1/001')])
        with patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice.L10n_Vn_Edi_ViettelSinvoiceSymbol._l10n_vn_edi_lookup_symbols', return_value=request_response):
            self.env['l10n_vn_edi_viettel.sinvoice.symbol'].with_company(self.company_vn_1).action_fetch_symbols()

        symbols = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].with_context(active_test=False).search([
            ('company_id', '=', self.company_vn_1.id),
        ])
        self.assertRecordValues(symbols, [
            {'name': 'C23TSA', 'active': True},
            {'name': 'C23TSB', 'active': False},
        ])

    def test_fetch_symbols_multicompany(self):
        """Each company's symbols should be fetched and stored independently, non-VN companies should be ignored."""
        def mock_lookup(company):
            if company == self.company_vn_1:
                return self._mock_api_fetch_symbols([('C23TSA', '1/001')])
            return self._mock_api_fetch_symbols([('C23TSB', '1/002')])

        multicompany_env = self.env(context={**self.env.context, 'allowed_company_ids': (self.company_vn_1 | self.company_vn_2 | self.company_us).ids})

        with patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice.L10n_Vn_Edi_ViettelSinvoiceSymbol._l10n_vn_edi_lookup_symbols', side_effect=mock_lookup):
            multicompany_env['l10n_vn_edi_viettel.sinvoice.symbol'].action_fetch_symbols()

        symbols_1 = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].search([('company_id', '=', self.company_vn_1.id)])
        symbols_2 = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].search([('company_id', '=', self.company_vn_2.id)])
        symbols_us = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].search([('company_id', '=', self.company_us.id)])

        self.assertRecordValues(symbols_1, [{'name': 'C23TSA', 'invoice_template_code': '1/001'}])
        self.assertRecordValues(symbols_2, [{'name': 'C23TSB', 'invoice_template_code': '1/002'}])
        self.assertFalse(symbols_us, "Non-VN company should have no symbols created")

    def test_fetch_symbols_multicompany_no_cross_archive(self):
        """Archiving symbols for one company should not affect another company's symbols."""
        multicompany_env = self.env(context={**self.env.context, 'allowed_company_ids': (self.company_vn_1 | self.company_vn_2).ids})

        request_response = self._mock_api_fetch_symbols([('C23TSA', '1/001')])
        with patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice.L10n_Vn_Edi_ViettelSinvoiceSymbol._l10n_vn_edi_lookup_symbols', return_value=request_response):
            multicompany_env['l10n_vn_edi_viettel.sinvoice.symbol'].action_fetch_symbols()

        def mock_lookup_after(company):
            if company == self.company_vn_1:
                return self._mock_api_fetch_symbols([])  # C23TSA dropped for company 1
            return self._mock_api_fetch_symbols([('C23TSA', '1/001')])  # Still present for company 2

        with patch('odoo.addons.l10n_vn_edi_viettel.models.sinvoice.L10n_Vn_Edi_ViettelSinvoiceSymbol._l10n_vn_edi_lookup_symbols', side_effect=mock_lookup_after):
            multicompany_env['l10n_vn_edi_viettel.sinvoice.symbol'].action_fetch_symbols()

        symbols = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].with_context(active_test=False).search([
            ('company_id', 'in', (self.company_vn_1 | self.company_vn_2).ids),
        ])
        self.assertRecordValues(symbols, [
            {'company_id': self.company_vn_1.id, 'name': 'C23TSA', 'active': False},
            {'company_id': self.company_vn_2.id, 'name': 'C23TSA', 'active': True},
        ])
