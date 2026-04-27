
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    iso20022_orgid_id = fields.Char('Identification', size=35, copy=False, compute='_compute_iso20022_orgid', readonly=False, store=True,
        help="Identification assigned by an institution (eg. VAT number).")
    iso20022_orgid_issr = fields.Char('Issuer', size=35, copy=False, compute='_compute_iso20022_orgid', readonly=False, store=True,
        help="Entity that assigns the identification (eg. KBE-BCO or Finanzamt Muenchen IV).")
    iso20022_initiating_party_name = fields.Char('Your Company Name', size=70, copy=False,
        help="Will appear as the name of the party initiating the payment. Limited to 70 characters.")
    iso20022_lei = fields.Char(related='partner_id.iso20022_lei', readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Overridden in order to set the name of the company as default value
            # for iso20022_initiating_party_name field
            name = vals.get('name')
            if name and 'iso20022_initiating_party_name' not in vals:
                vals['iso20022_initiating_party_name'] = self.env['account.journal']._sepa_sanitize_communication(name)
        return super().create(vals_list)

    @api.depends('partner_id.country_id')
    def _compute_iso20022_orgid(self):
        """ Set default value if missing for :
            - iso20022_orgid_issr, which correspond to the field 'Issuer' of an 'OrganisationIdentification', as described in ISO 20022.
            - iso20022_orgid_id, which correspond to the field 'Identification' of an 'OrganisationIdentification', as described in ISO 20022.
        """
        for company in self:
            if company.iso20022_orgid_id or company.iso20022_orgid_issr:
                continue
            if company.partner_id.country_id.code == 'BE':
                company.iso20022_orgid_issr = 'KBO-BCE'
                company.iso20022_orgid_id = company.vat[:2].upper() + company.vat[2:].replace(' ', '') if company.vat else ''
            else:
                company.iso20022_orgid_issr = ''
                company.iso20022_orgid_id = ''
