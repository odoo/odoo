# -*- coding: utf-8 -*-
{
    'name': 'Education Billing (SIF Education)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Education',
    'summary': 'Manajemen Tagihan Pendidikan SPP & UKT Terintegrasi Pendapatan & Buku Besar',
    'description': """
Modul Education Billing
=======================
Manajemen tagihan pendidikan (SMP, SMA, SMK, Universitas).

Fitur Utama:
- Master Sekolah / Institusi Pendidikan (SMP, SMA, SMK, Universitas).
- Master Tahun Ajaran, Semester, Jurusan, dan Kelas.
- Master Siswa / Mahasiswa & Data Orang Tua / Wali (dengan kontak HP/WhatsApp/Email).
- Tagihan SPP (Bulanan) & UKT (Semesteran).
- Mass Billing Generator Wizard per jenjang / kelas / semester.
- Verifikasi Pembayaran oleh Staf Sekolah / Kampus.
- Auto-post Pendapatan ke modul `pendapatan` dan `sif_keuangan` (Jurnal Besar).
- Reminder Pembayaran ke Orang Tua / Siswa (WhatsApp helper & Email reminder).
- Laporan & Kwitansi Pembayaran PDF.
    """,
    'author': 'Konsulta / SIFNEXT',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'pendapatan',
        'sif_keuangan',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/education_data.xml',
        'wizard/education_bill_generate_wizard_views.xml',
        'wizard/education_bill_reject_wizard_views.xml',
        'wizard/education_reminder_wizard_views.xml',
        'wizard/education_bill_mass_update_wizard_views.xml',
        'views/education_school_views.xml',
        'views/education_academic_views.xml',
        'views/education_parent_views.xml',
        'views/education_student_views.xml',
        'views/education_bill_views.xml',
        'views/education_menu_views.xml',
        'report/report_kwitansi.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
}
