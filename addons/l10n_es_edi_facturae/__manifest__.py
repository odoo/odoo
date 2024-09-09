# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spain - Facturae EDI',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.facturae.gob.es/face/Paginas/FACE.aspx',
    'description': """
This module create the Facturae file required to send the invoices information to the General State Administrations.
It allows the export and signature of the signing of Facturae files.
The current version of Facturae supported is the 3.2.2

for more informations, see https://www.facturae.gob.es/face/Paginas/FACE.aspx
    """,
    'depends': [
        'certificate',
        'l10n_es',
    ],
    'data': [
        'data/uom.uom.csv',
        'data/facturae_templates.xml',
        'data/l10n_es_edi_facturae.ac_role_type.csv',
        'data/signature_templates.xml',

        'security/ir.model.access.csv',

        'views/l10n_es_edi_facturae_views.xml',
        'views/res_partner_views.xml',
        'views/account_tax_views.xml',
        'views/account_move_views.xml',
        'views/uom_uom_views.xml',
        'views/account_menuitem.xml',

        'wizard/account_move_reversal_view.xml',
    ],
    'demo': [
        'demo/l10n_es_edi_facturae_demo.xml',
    ],
    'post_init_hook': '_l10n_es_edi_facturae_post_init_hook',
    'installable': True,
    'auto_install': ['l10n_es'],
    'license': 'LGPL-3',
}
