{
    'name': 'RKA',
    'version': '19.0.2.5.0',
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
        'security/rka_security.xml',
        'security/ir.model.access.csv',
        'views/rka_budget_views.xml',
        'reports/beban_usaha_report.xml',
        'views/dashboard_menu.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'sif_rka/static/src/js/dashboard_chart.js',
            'sif_rka/static/src/xml/bar_chart_action.xml',
            'sif_rka/static/src/scss/dashboard_chart.scss',
        ],
    },

    'installable': True,
    'application': True,
}
