# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, models

from odoo.addons.l10n_bd.tools.partner_identifiers import BD_ADDITIONAL_IDENTIFIERS_METADATA

BD_BIN_RE = re.compile(r'\d{13}')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **BD_ADDITIONAL_IDENTIFIERS_METADATA}

    def format_vat_bd(self, vat):
        vat = (vat or '').replace('-', '').replace(' ', '')
        if BD_BIN_RE.fullmatch(vat):
            return f'{vat[:9]}-{vat[9:]}'
        return vat

    def check_vat_bd(self, vat):
        # BIN: 13 digits, written 123456789-0101 (9-digit base + 4-digit branch).
        return bool(BD_BIN_RE.fullmatch((vat or '').replace('-', '').replace(' ', '')))
