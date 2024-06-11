# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ke_exemption_number = fields.Char(
        string='Exemption Number',
        help='The exemption number of the partner. Provided by the Kenyan government.',
    )

    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_ke_exemption_number']
