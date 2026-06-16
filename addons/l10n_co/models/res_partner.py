# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

FINAL_CONSUMER_VAT = '222222222222'  # 'Consumidor Final', the generic partner used in B2C

# Map a Colombian identifier to its DIAN identification type code (catalog used in the EDI
# documents and the exogenous reports). The NIT lives on `vat` and is resolved separately.
CO_FOREIGN_ID_DIAN_CODE = '42'   # Documento de identificación extranjero (typed foreign id)
CO_FOREIGN_VAT_DIAN_CODE = '50'  # NIT de otro país (foreign tax number on `vat`)
CO_IDENTIFIER_TO_DIAN_CODE = {
    'CO_NIT': '31',
    'CO_CC': '13',
    'CO_RC': '11',
    'CO_TI': '12',
    'CO_TE': '21',
    'CO_CE': '22',
    'CO_NIUP': '91',
    'CO_PEP': '47',
    'CO_PPT': '48',
    'PASSPORT': '41',
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_co_dian_code = fields.Char(
        string='CO Identification Type Code',
        compute='_compute_l10n_co_identification',
        store=True,
        readonly=True,
    )
    l10n_co_id_number = fields.Char(
        string='CO Identification Number',
        compute='_compute_l10n_co_identification',
        store=True,
        readonly=True,
    )

    @api.depends(
        'vat', 'country_id', 'additional_identifiers',
        'commercial_partner_id.vat', 'commercial_partner_id.country_id',
        'commercial_partner_id.additional_identifiers',
    )
    def _compute_l10n_co_identification(self):
        for partner in self:
            partner.l10n_co_dian_code = partner._l10n_co_get_dian_code()
            partner.l10n_co_id_number = partner._get_preferred_legal_entity_identifier_vals().get('value', '')

    @api.depends(
        'vat', 'country_id', 'additional_identifiers',
        'commercial_partner_id.vat', 'commercial_partner_id.country_id',
        'commercial_partner_id.additional_identifiers',
    )
    def _compute_is_company(self):
        co_partners = self.filtered(lambda p: p.country_code == 'CO')
        # 'Consumidor Final' is a person regardless of its (placeholder) identification.
        consumidor_final = self.env.ref('l10n_co_edi.consumidor_final_customer', raise_if_not_found=False) \
            or self.env['res.partner']
        for partner in co_partners - consumidor_final:
            # A Colombian partner is a company when identified by a NIT, as opposed to a natural
            # person (Cédula de ciudadanía, ...); a partner cannot hold both at once.
            partner.is_company = partner._get_preferred_legal_entity_identifier_vals().get('key') == 'CO_NIT'
        super(ResPartner, self - co_partners)._compute_is_company()

    def _l10n_co_get_dian_code(self):
        """ Return the DIAN identification type code for this partner, derived from the
        partner's preferred legal entity identifier (the same pick used for the id number,
        so code and value always agree).

        Resolution order:
            1. NIT (CO vat) or a CO person identifier (CC, RC, TI, …) / Passport → its mapped code.
            2. A tax id from another country → '50' (NIT de otro país).
            3. A typed identifier from another country → '42' (foreign document).
            4. No determinable identification → '50' (NIT de otro país), the pre-refactor default.
        """
        vals = self._get_preferred_legal_entity_identifier_vals()
        key = vals.get('key')
        if key in CO_IDENTIFIER_TO_DIAN_CODE:  # CO NIT (vat) or a CO person identifier
            return CO_IDENTIFIER_TO_DIAN_CODE[key]
        if vals.get('category') in ('TIN', 'VAT', 'GST'):  # a tax id from another country
            return CO_FOREIGN_VAT_DIAN_CODE
        if key:  # a typed identifier from another country
            return CO_FOREIGN_ID_DIAN_CODE
        return CO_FOREIGN_VAT_DIAN_CODE
