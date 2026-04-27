# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_de_datev_identifier = fields.Integer(
        string='DateV Vendor',
        copy=False,
        tracking=True,
        company_dependent=True,
        index='btree_not_null',
        help="In the DateV export of the General Ledger, each vendor will be identified by this identifier. "
        "If this identifier is not set, the database id of the partner will be added to a multiple of ten starting by the number 7."
        "The account code's length can be specified in the company settings."
    )
    l10n_de_datev_identifier_customer = fields.Integer(
        string='DateV Customer',
        copy=False,
        tracking=True,
        company_dependent=True,
        index='btree_not_null',
        help="In the DateV export of the General Ledger, each customer will be identified by this identifier. "
        "If this identifier is not set, the database id of the partner will be added to a multiple of ten starting by the number 1."
        "The account code's length can be specified in the company settings."
    )

    @api.constrains('l10n_de_datev_identifier')
    def _check_datev_identifier(self):
        partners = self.filtered('l10n_de_datev_identifier')
        identifiers = partners.mapped('l10n_de_datev_identifier')
        if not len(partners) == len(set(identifiers)) == self.with_context(active_test=False).search_count(
                [('l10n_de_datev_identifier', 'in', identifiers)], limit=len(identifiers) + 1):
            raise ValidationError(_('You have already defined a partner with the same Datev identifier. '))

    @api.constrains('l10n_de_datev_identifier_customer')
    def _check_datev_identifier_customer(self):
        partners = self.filtered('l10n_de_datev_identifier_customer')
        identifiers = partners.mapped('l10n_de_datev_identifier_customer')
        if not len(partners) == len(set(identifiers)) == self.with_context(active_test=False).search_count(
                [('l10n_de_datev_identifier_customer', 'in', identifiers)], limit=len(identifiers) + 1):
            raise ValidationError(_('You have already defined a partner with the same Datev Customer identifier'))
