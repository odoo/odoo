# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestEhoadonBuyer(TransactionCase):
    def _move(self, partner):
        return self.env['account.move'].create({'move_type': 'out_invoice', 'partner_id': partner.id})

    def test_partner_without_vat_is_retail_consumer(self):
        partner = self.env['res.partner'].create({'name': 'Khách lẻ'})
        customer = self._move(partner)._ehoadon_build_invoice_customer()
        self.assertEqual(customer['taxNumber'], '')
        self.assertEqual(customer['companyName'], 'Bán cho người tiêu dùng')

    def test_partner_with_vat_maps_company_buyer(self):
        company = self.env['res.partner'].create({
            'name': 'Cong ty ABC',
            'is_company': True,
            'vat': ' 0312345678 ',
            'street': '1 Le Loi',
            'city': 'HCM',
        })
        contact = self.env['res.partner'].create({'name': 'Nguyen Van A', 'parent_id': company.id})
        customer = self._move(contact)._ehoadon_build_invoice_customer()
        self.assertEqual(customer['taxNumber'], '0312345678')
        self.assertEqual(customer['companyName'], 'Cong ty ABC')
        self.assertEqual(customer['fullName'], 'Nguyen Van A')
        self.assertIn('1 Le Loi', customer['address'])
        self.assertNotIn('\n', customer['address'])

    def test_einvoice_tab_overrides_partner_data(self):
        partner = self.env['res.partner'].create({
            'name': 'Ten Contact',
            'vat': '0312345678',
            'einvoice_vat': ' 0109876543 ',
            'einvoice_name': 'Cong ty Xuat HD',
            'einvoice_buyer_name': 'Don vi Xuat HD',
            'einvoice_address': '9 Tran Hung Dao',
        })
        customer = self._move(partner)._ehoadon_build_invoice_customer()
        self.assertEqual(customer['taxNumber'], '0109876543')
        self.assertEqual(customer['companyName'], 'Cong ty Xuat HD')
        self.assertEqual(customer['fullName'], 'Don vi Xuat HD')
        self.assertEqual(customer['address'], '9 Tran Hung Dao')

    def test_einvoice_tab_without_vat_is_not_consumer(self):
        partner = self.env['res.partner'].create({
            'name': 'Khach co CCCD',
            'einvoice_name': 'Nguyen Van B',
            'einvoice_partner_id': '079123456789',
        })
        customer = self._move(partner)._ehoadon_build_invoice_customer()
        self.assertEqual(customer['taxNumber'], '')
        self.assertEqual(customer['companyName'], 'Nguyen Van B')
        self.assertEqual(customer['address'], 'Người mua không cung cấp địa chỉ')
