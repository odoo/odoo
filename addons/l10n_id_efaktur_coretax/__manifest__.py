# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesia E-faktur (Coretax)',
    'icon': '/account/static/description/l10n.png',
    'version': '1.0',
    'description': """
        E-invoicing feature provided by DJP (Indonesian Tax Office). As of January 1st 2025,
        Indonesia is using CoreTax system, which changes the file format and content of E-Faktur.
        We're changing from CSV files into XML.
        At the same time, due to tax regulation changes back and forth, for general E-Faktur now,
        TaxBase (DPP) has to be mulitplied by factor of 11/12 while multiplied to tax of 12% which
        is resulting to 11%.
    """,
    'category': 'Accounting/Localizations/EDI',
    'depends': ['l10n_id', 'l10n_id_efaktur'],
    'data': [
        # New Data Import (E-Faktur code related)
        "data/l10n_id_efaktur_coretax.product.code.csv",
        "data/l10n_id_efaktur_coretax.uom.code.csv",
        "data/uom.uom.csv",
        "data/efaktur_templates.xml",
        "data/ir_action.xml",

        # Accesses
        "security/ir.model.access.csv",

        # Views
        "views/product_template.xml",
        "views/product_code.xml",
        "views/res_partner.xml",
        "views/account_move.xml",
        "views/efaktur_document.xml",
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_post_init_hook',
    'license': 'LGPL-3',
}
