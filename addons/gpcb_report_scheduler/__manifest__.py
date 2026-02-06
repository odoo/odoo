# Part of GPCB. See LICENSE file for full copyright and licensing details.
{
    'name': 'GPCB Report Scheduler',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Automated generation, review, and delivery of recurring tax reports',
    'description': """
GPCB Report Scheduler
=====================

Automates the lifecycle of recurring Colombian tax reports and financial statements:

- **Schedule definitions** — Configure frequency, lead days, auto-filing, and recipients
- **Report generation** — Automatic generation of IVA, withholding, exogenous, and
  financial reports via daily cron
- **Review workflow** — Optional human review before filing or delivery
- **Email delivery** — Send reports to configured recipients with PDF attachments
- **Audit trail** — Full history of every generation, review, and delivery
- **Pre-configured Colombian schedules** — Formulario 300, 350, withholding certs,
  exogenous information with standard filing frequencies
    """,
    'depends': [
        'account',
        'mail',
        'l10n_co_edi',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/report_schedule_data.xml',
        'views/report_schedule_views.xml',
    ],
    'installable': True,
    'author': 'GPCB',
    'license': 'LGPL-3',
}
