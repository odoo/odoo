# -*- coding: utf-8 -*-
{
    "name": "Transaksi Bank",
    "summary": "Mutasi Antar Rekening dan Alur Persetujuan Transfer Bank",
    "version": "19.0.2.0.0",
    "category": "Accounting/Accounting",
    "author": "Konsulta",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "sif_keuangan",
        "sifnext_ppl",
        "sifnext_org",
    ],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "wizard/transaction_reject_wizard_views.xml",
        "views/transaction_views.xml",
        "views/ppl_views.xml",
        "views/menu_views.xml",
    ],
    "application": True,
    "installable": True,
}
