# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from .account_journal import sanitize_communication

class ResCompany(models.Model):
    _inherit = "res.company"

    # TODO : complete methods _default_sepa_origid_id and _default_sepa_origid_issr for all countries of the SEPA

    sepa_orgid_id = fields.Char('Identification', size=35, copy=False, compute='_compute_sepa_origid', readonly=False, store=True,
        help="Identification assigned by an institution (eg. VAT number).")
    sepa_orgid_issr = fields.Char('Issuer', size=35, copy=False, compute='_compute_sepa_origid', readonly=False, store=True,
        help="Entity that assigns the identification (eg. KBE-BCO or Finanzamt Muenchen IV).")
    sepa_initiating_party_name = fields.Char('Your Company Name', size=70, copy=False,
        help="Will appear in SEPA payments as the name of the party initiating the payment. Limited to 70 characters.")
    account_sepa_lei = fields.Char(related='partner_id.account_sepa_lei', readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Overridden in order to set the name of the company as default value
            # for sepa_initiating_party_name field
            name = vals.get('name')
            if name and 'sepa_initiating_party_name' not in vals:
                vals['sepa_initiating_party_name'] = sanitize_communication(name)

        return super().create(vals_list)

    @api.depends('partner_id.country_id')
    def _compute_sepa_origid(self):
        """ Set default value for :
            - sepa_orgid_issr, which correspond to the field 'Issuer' of an 'OrganisationIdentification', as described in ISO 20022.
            - sepa_orgid_id, which correspond to the field 'Identification' of an 'OrganisationIdentification', as described in ISO 20022.
        """
        for company in self:
            if company.partner_id.country_id.code == 'BE':
                company.sepa_orgid_issr = 'KBO-BCE'
                company.sepa_orgid_id = company.vat[:2].upper() + company.vat[2:].replace(' ', '') if company.vat else ''
            else:
                company.sepa_orgid_issr = ''
                company.sepa_orgid_id = ''
