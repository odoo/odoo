# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Colombia - Electronic Invoicing (DIAN)',
    'countries': ['co'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    'summary': 'Electronic invoicing for Colombia via DIAN (facturacion electronica)',
    'description': """
Colombian Electronic Invoicing — DIAN Compliance
=================================================

Implements Colombian electronic invoicing (facturacion electronica) per:
- Resolucion 000165 de 2023
- DIAN Technical Annex v1.9 (UBL 2.1)
- Decreto 2242 de 2015 (digital signatures)
- Art. 616-1 Estatuto Tributario

Features:
- CUFE/CUDE hash generation (SHA-384)
- UBL 2.1 XML generation with DIAN extensions
- Digital certificate management (XMLDSig)
- DIAN web service integration (pre-validation model)
- QR code generation for graphic representation
- DIAN-authorized numbering range management
- UVT (Unidad de Valor Tributario) management
- Contingency numbering support
    """,
    'depends': [
        'l10n_co',
        'account_edi',
        'account_edi_ubl_cii',
        'l10n_latam_invoice_document',
        'l10n_account_withholding_tax',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_edi_format_data.xml',
        'data/l10n_co_edi.payment.means.csv',
        'data/l10n_co_edi.tax.type.csv',
        'data/l10n_co_edi.document.type.csv',
        'data/l10n_co_edi.fiscal.responsibility.csv',
        'data/l10n_co_edi.uvt.csv',
        'data/ir_cron_data.xml',
        'data/account_fiscal_position_data.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_fiscal_position_views.xml',
        'views/l10n_co_edi_uvt_views.xml',
        'views/l10n_co_withholding_cert_views.xml',
        'report/l10n_co_withholding_cert_report.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_co', 'account_edi'],
    'author': 'GPCB',
    'license': 'LGPL-3',
}
