# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Chilean eCommerce',
    'version': '0.0.1',
    'category': 'Accounting/Localizations/Website',
    'sequence': 14,
    'author': 'Blanco Martín & Asociados',
    'depends': [
        'website_sale',
        'l10n_cl_edi'
    ],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_cl_edi_website_sale/static/src/js/fields/l10n_cl_fields.js',
            # TODO in master: This should not be imported in the manifest, it
            # should be an ir.asset instead. We used this solution to be able to
            #  fix the bug without any module update.
            'l10n_cl_edi_website_sale/static/src/snippets/s_website_form/000.js',
        ]
    },
    'license': 'OEEL-1',
}
