# Part of GPCB. See LICENSE file for full copyright and licensing details.
{
    'name': 'Colombia - Electronic Payroll (Nomina Electronica)',
    'countries': ['co'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'DIAN electronic payroll support documents (nomina electronica)',
    'description': """
Colombian Electronic Payroll — DIAN Compliance
===============================================

Implements electronic payroll support documents (documentos soporte de nomina
electronica) per Resolucion 000013 de 2021:

- **Standalone payroll EDI** — Import payroll data from external systems
  (Novasoft, Siigo, generic CSV) and transmit to DIAN
- **CUNE generation** — Codigo Unico de Nomina Electronica (SHA-384)
- **UBL XML generation** — Nomina Individual and Nomina de Ajuste
- **Digital signature** — Reuses certificate infrastructure from l10n_co_edi
- **DIAN submission** — Reuses web service client from l10n_co_edi
- **Accounting entries** — Auto-generate journal entries from confirmed payroll
- **Import wizard** — CSV upload with configurable column mapping
- **Colombian labor concepts** — Earnings, deductions, and provisions per law
    """,
    'depends': [
        'hr',
        'account',
        'l10n_co_edi',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_co_payroll_edi_data.xml',
        'views/l10n_co_payroll_document_views.xml',
    ],
    'installable': True,
    'author': 'GPCB',
    'license': 'LGPL-3',
}
