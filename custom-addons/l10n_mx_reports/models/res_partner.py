# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.misc import get_lang


class ResPartner(models.Model):
    """Inherited to complete the attributes required to DIOT Report

    Added required fields according with the provisions in the next SAT
    document `Document <goo.gl/THPLDk>`_. To allow generate the form A-29
    requested by this SAT.
    """
    _inherit = 'res.partner'

    l10n_mx_type_of_third = fields.Char(
        compute='_compute_type_of_third',
        help='Mexico: Describes what type of third party the supplier is. This is the first column in DIOT report.')
    l10n_mx_type_of_operation = fields.Selection([
        ('03', ' 03 - Provision of Professional Services'),
        ('06', ' 06 - Renting of buildings'),
        ('85', ' 85 - Others')],
        help='Mexico: The type of operations that this supplier performs. This is the second column in DIOT report.',
        string='Type of Operation',
    )
    l10n_mx_nationality = fields.Char(
        help='Mexico: Nationality based in the supplier country. Is the seventh column in DIOT report.',
        compute='_compute_nationality', readonly=True)

    @api.depends('country_id')
    def _compute_type_of_third(self):
        """Get the type of third to use in DIOT report.
        04 is to National Supplier
        05 to Foreign Supplier"""
        for partner in self:
            partner_type = '04' if partner.country_id.code == "MX" else '05'
            partner.l10n_mx_type_of_third = partner_type

    @api.depends('country_id')
    def _compute_nationality(self):
        default_lang = get_lang(self.env, lang_code='es_MX').code
        for partner in self:
            partner.l10n_mx_nationality = partner.country_id.with_context(
                lang=default_lang).demonym

    def _get_not_partners_diot(self):
        partners = self.mapped('commercial_partner_id')
        return partners.filtered(lambda r: any([
            (not r.vat and r.l10n_mx_type_of_third == '04'),
            not r.l10n_mx_type_of_third, not r.l10n_mx_type_of_operation,
            (r.l10n_mx_type_of_third == '05' and not r.country_id.code),
            (r.l10n_mx_type_of_third == '04' and not r.check_vat_mx(r.vat))]))
