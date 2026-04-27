# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll - DmfA SFTP',
    'countries': ['be'],
    'category': 'Human Resources',
    'depends': ['l10n_be_hr_payroll', 'certificate'],
    'external_dependencies': {
        'python': ['paramiko']
    },
    'description': """
synchronize DmfA to ONSS portal
===============================

This new module automates the synchronization of DmfA ONSS declarations
to the official Belgian SFTP portal.

It integrates with the existing `l10n_be_hr_payroll` and
`l10n_be_hr_payroll_dmfa` modules to:

- Upload the FO, FS, and GO files to the correct ONSS environment folder
  (IN, INTEST, INTEST-S).
- Poll the OUT folders (OUT, OUTTEST, OUTTEST-S) for returned files.
- Link received files to the corresponding declarations and employees
  when applicable.

Technical features include:
- Secure connection using a private key and technical user credentials.
- XML file parsing for ACRF and notification files.
- Error handling and logging for missing directories or malformed files.

This module ensures compliance with ONSS electronic declaration
requirements and reduces manual interaction with the SFTP portal.
    """,
    'data': [
        'views/hr_dmfa_views.xml',
        'views/res_config_settings_views.xml',
        'views/l10n_be_onss_file_views.xml',
        'views/l10n_be_onss_declaration_views.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_cron_data.xml',
    ],
    'license': 'OEEL-1',
}
