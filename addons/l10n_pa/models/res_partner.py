# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models
from odoo.tools import SQL
from odoo.addons.l10n_pa.tools.partner_identifiers import PA_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pa_corregimiento = fields.Many2one(
        comodel_name='l10n_pa.res.city.corregimiento',
        string='Corregimiento',
        domain="[('city_id', '=?', city_id)]",
        help='Corregimientos are part of a district.',
    )
    l10n_pa_corregimiento_name = fields.Char(
        string='Corregimiento name',
        related='l10n_pa_corregimiento.name',
    )
    l10n_pa_dv = fields.Char(
        string='DV',
        size=2,
        help='Check digit from the DGI',
    )
    l10n_pa_taxpayer_type = fields.Selection(
        selection=[('1', 'Natural Person'), ('2', 'Legal Entity')],
        string='Taxpayer Type (PA)',
        compute='_compute_l10n_pa_taxpayer_type',
        store=True,
        readonly=False,
        init_storage='_init_column_l10n_pa_taxpayer_type',
        help='DGI taxpayer type, derived from the RUC format by default.',
    )

    def _init_column_l10n_pa_taxpayer_type(self):
        self.env.execute_query(SQL("""
            UPDATE res_partner p
               SET l10n_pa_taxpayer_type = CASE
                       WHEN p.vat ~ '^(1[0-3]|[1-9]|PE|E|N)-[0-9]+-[0-9]+$' OR '-' || p.vat || '-' LIKE '%%-NT-%%' THEN '1'
                       ELSE '2'
                   END
              FROM res_country c
             WHERE c.id = p.country_id
               AND c.code = 'PA'
               AND p.vat IS NOT NULL
               AND p.vat != ''
        """))

    @api.depends('vat', 'country_code')
    def _compute_l10n_pa_taxpayer_type(self):
        for partner in self:
            if partner.country_code != 'PA' or not partner.vat:
                partner.l10n_pa_taxpayer_type = False
            # DGI natural person RUC: cédula of province 1 to 13, PE, E, N, or with an NT segment
            elif re.fullmatch(r'(1[0-3]|[1-9]|PE|E|N)-[0-9]+-[0-9]+', partner.vat) or 'NT' in partner.vat.split('-'):
                partner.l10n_pa_taxpayer_type = '1'
            else:
                partner.l10n_pa_taxpayer_type = '2'

    @api.onchange('l10n_pa_corregimiento')
    def _onchange_l10n_pa_corregimiento(self):
        if self.l10n_pa_corregimiento:
            self.city_id = self.l10n_pa_corregimiento.city_id

    @api.onchange('city_id')
    def _onchange_l10n_pa_city_id(self):
        if self.city_id and self.l10n_pa_corregimiento.city_id and self.l10n_pa_corregimiento.city_id != self.city_id:
            self.l10n_pa_corregimiento = False

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super()._formatting_address_fields() + ['l10n_pa_corregimiento_name']

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {
            **super()._get_all_additional_identifiers_metadata(),
            **PA_ADDITIONAL_IDENTIFIERS_METADATA,
        }
