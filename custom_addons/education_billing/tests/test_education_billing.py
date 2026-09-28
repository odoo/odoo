# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install', 'education_billing')
class TestEducationBilling(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # COA Pendapatan & Kas
        cls.coa_pendapatan = cls.env['sif.coa'].create({
            'code': '41100-TEST',
            'name': 'Pendapatan SPP/UKT Test',
            'account_type': 'income',
        })
        cls.coa_kas = cls.env['sif.coa'].create({
            'code': '11101-TEST',
            'name': 'Kas Penerimaan Test',
            'account_type': 'asset',
        })

        # Kategori Pendapatan
        cls.category = cls.env['pendapatan.category'].create({
            'name': 'Penerimaan SPP/UKT Pendidikan',
            'code': 'SPP-EDU-TEST',
            'periodicity': 'bulanan',
            'coa_pendapatan_id': cls.coa_pendapatan.id,
            'coa_kas_id': cls.coa_kas.id,
            'company_id': cls.company.id,
        })

        # Master Institusi (SMP & Univ)
        cls.school_smp = cls.env['education.school'].create({
            'name': 'SMP Test Mandiri',
            'code': 'SMP-TST',
            'level': 'smp',
            'default_spp_amount': 500000.0,
            'category_id': cls.category.id,
            'company_id': cls.company.id,
        })

        cls.school_univ = cls.env['education.school'].create({
            'name': 'Universitas Test Mandiri',
            'code': 'UNIV-TST',
            'level': 'univ',
            'default_ukt_amount': 5000000.0,
            'category_id': cls.category.id,
            'company_id': cls.company.id,
        })

        # Tahun Ajaran
        cls.academic_year = cls.env['education.academic.year'].create({
            'name': '2025/2026',
            'code': 'TA2526-TST',
            'start_date': '2025-07-01',
            'end_date': '2026-06-30',
            'is_current': True,
            'company_id': cls.company.id,
        })

        # Kelas SMP
        cls.class_smp = cls.env['education.class'].create({
            'name': 'VII-A',
            'code': '7A-TST',
            'school_id': cls.school_smp.id,
            'academic_year_id': cls.academic_year.id,
        })

        # Orang Tua
        cls.parent = cls.env['education.parent'].create({
            'name': 'Budi Santoso',
            'relation_type': 'ayah',
            'whatsapp': '081234567890',
            'email': 'budi@example.com',
            'company_id': cls.company.id,
        })

        # Siswa SMP
        cls.student_smp = cls.env['education.student'].create({
            'name': 'Ahmad Fauzi',
            'student_id_number': 'NISN-12345',
            'school_id': cls.school_smp.id,
            'class_id': cls.class_smp.id,
            'parent_id': cls.parent.id,
            'company_id': cls.company.id,
        })

        # Mahasiswa Univ
        cls.student_univ = cls.env['education.student'].create({
            'name': 'Rina Fitriani',
            'student_id_number': 'NIM-98765',
            'school_id': cls.school_univ.id,
            'parent_id': cls.parent.id,
            'company_id': cls.company.id,
        })

    def test_01_effective_amount_and_schemes(self):
        """Test skema tagihan default dan perhitungan tarif berlaku"""
        self.assertEqual(self.student_smp.billing_scheme, 'spp_bulanan')
        self.assertEqual(self.student_smp.effective_amount, 500000.0)

        self.assertEqual(self.student_univ.billing_scheme, 'ukt_semester')
        self.assertEqual(self.student_univ.effective_amount, 5000000.0)

        # Test WhatsApp phone cleaner
        clean_wa = self.parent.get_clean_whatsapp_number()
        self.assertEqual(clean_wa, '6281234567890')

    def test_02_generate_spp_bill_wizard(self):
        """Test generate tagihan SPP massal lewat wizard"""
        wizard = self.env['education.bill.generate.wizard'].create({
            'school_id': self.school_smp.id,
            'class_id': self.class_smp.id,
            'bill_type': 'spp',
            'month': '09',
            'year': 2026,
            'academic_year_id': self.academic_year.id,
            'target_state': 'unpaid',
        })
        action = wizard.action_generate_bills()
        self.assertTrue(action)

        bill = self.env['education.bill'].search([
            ('student_id', '=', self.student_smp.id),
            ('month', '=', '09'),
            ('year', '=', 2026),
        ])
        self.assertTrue(bill)
        self.assertEqual(bill.state, 'unpaid')
        self.assertEqual(bill.amount, 500000.0)
        self.assertEqual(bill.period_label, 'SPP September 2026')

    def test_03_staff_verification_flow_and_auto_pendapatan_jurnal(self):
        """Test alur verifikasi staf: Unpaid -> Waiting -> Verified -> Auto Masuk Pendapatan & Jurnal"""
        bill = self.env['education.bill'].create({
            'student_id': self.student_smp.id,
            'school_id': self.school_smp.id,
            'class_id': self.class_smp.id,
            'bill_type': 'spp',
            'month': '10',
            'year': 2026,
            'academic_year_id': self.academic_year.id,
            'amount': 500000.0,
            'state': 'draft',
            'category_id': self.category.id,
        })
        bill.action_publish_bill()
        self.assertEqual(bill.state, 'unpaid')

        # Siswa/Staf submit bukti pembayaran
        bill.write({
            'payment_method': 'transfer',
            'payment_ref': 'TRX-BANK-12345',
        })
        bill.action_submit_payment()
        self.assertEqual(bill.state, 'waiting_verification')

        # Staf verifikasi pembayaran
        bill.action_verify_payment()
        self.assertEqual(bill.state, 'verified')
        self.assertTrue(bill.pendapatan_id)
        self.assertEqual(bill.pendapatan_id.state, 'posted')
        self.assertEqual(bill.pendapatan_id.amount, 500000.0)

        # Verifikasi entri jurnal besar
        self.assertTrue(bill.pendapatan_id.journal_id)
        journal = bill.pendapatan_id.journal_id
        self.assertEqual(journal.state, 'posted')
        self.assertEqual(journal.total_debit, 500000.0)
        self.assertEqual(journal.total_credit, 500000.0)

    def test_04_staff_rejection_flow(self):
        """Test penolakan bukti pembayaran via wizard"""
        bill = self.env['education.bill'].create({
            'student_id': self.student_smp.id,
            'school_id': self.school_smp.id,
            'class_id': self.class_smp.id,
            'bill_type': 'spp',
            'month': '11',
            'year': 2026,
            'academic_year_id': self.academic_year.id,
            'amount': 500000.0,
            'state': 'waiting_verification',
            'category_id': self.category.id,
        })

        reject_wizard = self.env['education.bill.reject.wizard'].create({
            'bill_id': bill.id,
            'reason': 'Bukti transfer buram dan tidak terbaca.',
        })
        reject_wizard.action_confirm_reject()

        self.assertEqual(bill.state, 'rejected')
        self.assertEqual(bill.reject_reason, 'Bukti transfer buram dan tidak terbaca.')

    def test_05_reminder_message_generation(self):
        """Test susunan teks reminder untuk Orang Tua"""
        bill = self.env['education.bill'].create({
            'student_id': self.student_smp.id,
            'school_id': self.school_smp.id,
            'class_id': self.class_smp.id,
            'bill_type': 'spp',
            'month': '12',
            'year': 2026,
            'academic_year_id': self.academic_year.id,
            'amount': 500000.0,
            'state': 'unpaid',
            'category_id': self.category.id,
        })
        msg = bill.get_reminder_message()
        self.assertIn('Ahmad Fauzi', msg)
        self.assertIn('SPP Desember 2026', msg)
        self.assertIn('Rp 500.000', msg)

    def test_06_generate_ukt_bill_wizard_auto_type(self):
        """Test wizard generate otomatis mendeteksi UKT untuk jenjang universitas"""
        wizard_univ = self.env['education.bill.generate.wizard'].create({
            'school_id': self.school_univ.id,
            'semester': 'ganjil',
            'academic_year_id': self.academic_year.id,
            'target_state': 'unpaid',
        })
        self.assertEqual(wizard_univ.bill_type, 'ukt')
        action = wizard_univ.action_generate_bills()
        self.assertTrue(action)

        bill_univ = self.env['education.bill'].search([
            ('student_id', '=', self.student_univ.id),
            ('semester', '=', 'ganjil'),
            ('academic_year_id', '=', self.academic_year.id),
        ])
        self.assertTrue(bill_univ)
        self.assertEqual(bill_univ.bill_type, 'ukt')
        self.assertEqual(bill_univ.amount, 5000000.0)
