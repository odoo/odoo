# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    _sii_taxpayer_types = [
        ('1', 'IVA Afecto 1ra Categoría'),
        ('2', 'Emisor de Boletas 2da Categoría'),
        ('3', 'Consumidor Final'),
        ('4', 'Extranjero'),
    ]

    l10n_cl_sii_taxpayer_type = fields.Selection(
        _sii_taxpayer_types,
        'Taxpayer Types',
        index=True,
        default='1',
        help='1 - IVA Afecto (la mayoría de los casos)\n'
        '2 - Emisor Boletas (aplica solo para proveedores emisores de boleta)\n'
        '3 - Consumidor Final (se le emitirán siempre boletas)\n'
        '4 - Extranjero'
    )
