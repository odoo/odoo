from lxml import etree

from odoo import api, fields, models
from odoo.addons.l10n_co_dian import xml_utils


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_co_dian_enable_update_data = fields.Boolean(compute='_compute_l10n_co_dian_enable_update_data')

    @api.depends_context('company')
    @api.depends('l10n_latam_identification_type_id', 'vat')
    def _compute_l10n_co_dian_enable_update_data(self):
        for partner in self:
            company = self.env.company
            partner.l10n_co_dian_enable_update_data = (company.account_fiscal_country_id.code == 'CO'
                                                       and partner.l10n_latam_identification_type_id
                                                       and partner.vat)

    # if country_code is not part of the onchange then the _l10n_co_dian_update_data method
    # will not correctly trigger if the user fills in the l10n_latam_identification_type_id and
    # vat fields before filling in the country field
    @api.onchange('l10n_latam_identification_type_id', 'vat')
    def _l10n_co_dian_onchange_identification_type(self):
        for partner in self:
            company = self.env.company
            if partner.l10n_co_dian_enable_update_data and company.sudo().l10n_co_dian_certificate_ids:
                partner._l10n_co_dian_update_data(company)

    def button_l10n_co_dian_refresh_data(self):
        self._l10n_co_dian_update_data(self.env.company)

    def _l10n_co_dian_update_data(self, company):
        self.ensure_one()
        data = self._l10n_co_dian_call_get_acquirer({
            'identification_type': self._l10n_co_edi_get_carvajal_code_for_identification_type(),
            'identification_number': self._get_vat_without_verification_code(),
            'company': company,
        })

        if data:
            self.write(data)

    @api.model
    def _l10n_co_dian_call_get_acquirer(self, data: dict):
        if not self.env.ref('l10n_co_dian.get_acquirer', raise_if_not_found=False):
            # Could happen when the user did not update their db
            return dict()

        response = xml_utils._build_and_send_request(
            self,
            payload={
                'identification_type': data['identification_type'],
                'identification_number': data['identification_number'],
                'soap_body_template': "l10n_co_dian.get_acquirer",
            },
            service='GetAcquirer',
            company=data['company'],
        )

        if response['status_code'] != 200:
            return dict()

        root = etree.fromstring(response['response'])
        return {
            'email': root.findtext('.//{*}ReceiverEmail'),
            'name': root.findtext('.//{*}ReceiverName'),
        }
