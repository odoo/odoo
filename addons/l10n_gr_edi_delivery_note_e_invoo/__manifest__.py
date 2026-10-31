# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'author': 'Odoo S.A.',
    'name': 'Greece - myDATA Delivery Note through e-invoo',
    'category': 'Accounting/Localizations',
    'summary': """Transmit Greece myDATA EDI for Delivery Notes through e-invoo""",
    'description': """
        This module allows transmitting electronic Delivery Notes
        to Greece's tax authority myDATA platform through e-invoo.
    """,
    'countries': ['gr'],
    'depends': [
        'l10n_gr_edi_delivery_note',
        'l10n_gr_edi_e_invoo',
        'l10n_gr_edi_e_invoo_bridge',
    ],
    'data': [],
    'auto_install': True,
    'license': 'LGPL-3',
}
