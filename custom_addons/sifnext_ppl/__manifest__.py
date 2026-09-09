{
    "name": "SIFNEXT PPL",
    "summary": "Permintaan Pembayaran Langsung",
    "author": "SIFNEXT",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "license": "LGPL-3",
    "depends": ["account", "mail", "sif_keuangan", "hr_payroll_custom", "sif_rka"],
    "data": [
        "security/ppl_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        # Local/UAT fixture. Remove this entry from production deployments.
        "data/ppl_uat_users.xml",
<<<<<<< HEAD
=======
        "wizard/ppl_reject_wizard_views.xml",
>>>>>>> origin/sif-main-19
        "views/ppl_views.xml",
        "views/unit_views.xml",
        "views/payroll_integration_views.xml",
    ],
    "application": True,
    "installable": True,
}
