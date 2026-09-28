# -*- coding: utf-8 -*-
{
    'name': 'Pendapatan',
    'version': '19.0.1.1.0',
    'category': 'Accounting',
    'summary': 'Manajemen Pendapatan Organisasi (Bulanan & Semester)',
    'description': """
Modul Pendapatan
================
Modul untuk pencatatan & pengelolaan pendapatan organisasi/unit usaha.

Fitur:
- Master kategori pendapatan (SPP bulanan, uang semester, dll.)
- Periode: Bulanan & Semester
- Multi-level approval (Draft → Submitted → Approved → Posted)
- Auto-jurnal ke SIFNEXT Jurnal Besar (sif.jurnal.entry)
- Default COA Kas/Bank & COA Pendapatan per kategori
- Pendukung integrasi RKA (realisasi pendapatan via jurnal)
- Sequence nomor pendapatan otomatis

Use case:
- Perusahaan menaungi sekolah/universitas
- Pendapatan SPP bulanan & uang masuk semester
- Pendapatan unit usaha lain di bawah perusahaan
    """,
    'author': 'SIFNEXT',
    'website': '',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'mail',
        'sif_keuangan',
        'sifnext_org',
    ],

    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/pendapatan_category_data.xml',
        'views/pendapatan_category_views.xml',
        'views/pendapatan_views.xml',
        'wizard/laporan_pendapatan_wizard_views.xml',
        'views/menu_views.xml',
    ],

    'installable': True,
    'application': True,
}
