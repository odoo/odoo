{
    'name': 'SIF RKA',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Rencana Kerja dan Anggaran SIFNEXT',
    'description': '''
        Modul RKA untuk SIFNEXT ERP.

        Fitur:
        - Pengelolaan RKA tahunan
        - Anggaran bulanan otomatis
        - Filter berdasarkan tahun
        - Filter berdasarkan bulan
        - Realisasi otomatis dari Jurnal Besar
        - COA
        - Anggaran
        - Realisasi
        - Sisa anggaran
        - Persentase realisasi
        - Workflow pengajuan dan approval
    ''',
    'author': 'SIFNEXT',
    'website': '',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'sif_keuangan',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/rka_budget_views.xml',
        'reports/beban_usaha_report.xml',
    ],

    'installable': True,
    'application': True,
}