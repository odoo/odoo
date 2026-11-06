# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.l10n_pl.tools.partner_identifiers import PL_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    """Inherited to add the information needed for the JPK"""
    _inherit = 'res.partner'

    l10n_pl_links_with_customer = fields.Boolean(
        string='Links With Company',
        help='TP: Existing connection or influence between the customer and the supplier'
    )
    l10n_pl_county = fields.Char(string="County", help="Powiat")
    l10n_pl_municipality = fields.Char(string="Municipality", help="Gmina")

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ['l10n_pl_county', 'l10n_pl_municipality']

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **PL_ADDITIONAL_IDENTIFIERS_METADATA}
