# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountExternalTaxMixin(models.AbstractModel):
    _inherit = "account.external.tax.mixin"

    l10n_br_presence = fields.Selection(
        # Technical selection names are compatible with the API.
        [
            ('0', 'Not applicable'),
            ('1', 'Present'),
            ('2', 'Remote, internet'),
            ('3', 'Remote, phone'),
            ('4', 'NFC-e home delivery'),
            ('5', 'In-person operation, for establishment (v3)'),
            ('9', 'Remote, others'),
        ],
        compute='_compute_l10n_br_presence',
        store=True,
        readonly=False,
        string='Presence',
        help='Brazil: Defines if the buyer was physically present during the transaction, affecting tax calculation and location.'
    )
    l10n_br_service_operation_indicator = fields.Char(
        'Service Operation Indicator',
        help="Brazil: Defines the specific “indOp” operation indicator code for the service (e.g., '050101'). This value is sent to Avalara for tax calculation and invoice "
             "generation. If left empty, Avalara's automatic calculation may be used, but specific municipal validations may require a manual definition."
    )

    def _compute_l10n_br_presence(self):
        # To override elsewhere.
        for record in self:
            record.l10n_br_presence = '1'

    def _l10n_br_get_partner_type(self, partner):
        # Override.
        if not self.company_id.l10n_br_is_icbs:
            return super()._l10n_br_get_partner_type(partner)

        return partner.l10n_br_entity_type or super()._l10n_br_get_partner_type(partner)

    def _l10n_br_get_line_uom(self, line_id):
        # To override
        return False

    def _l10n_br_build_avatax_line(self, product, qty, unit_price, total, discount, line_id):
        # Override.
        res = super()._l10n_br_build_avatax_line(product, qty, unit_price, total, discount, line_id)
        if not self.company_id.l10n_br_is_icbs:
            return res

        if product.l10n_br_transaction_usage:
            res['usagePurpose'] = product.l10n_br_transaction_usage

        descriptor = res['itemDescriptor']
        if legal_reference := product.l10n_br_ncm_code_id.legal_reference:
            descriptor['legalReference'] = legal_reference

        if self.l10n_br_is_service_transaction:
            descriptor['hsCode'] = product.l10n_br_nbs_id.code
            descriptor['lc116Code'] = (product.l10n_br_ncm_code_id.code or '').replace('.', '')
        else:
            legal_uom = product.l10n_br_legal_uom_id
            line_uom = self._l10n_br_get_line_uom(line_id)

            goods = res.setdefault('goods', {})
            goods['notSubjectToIsTax'] = not product.l10n_br_taxable_is
            goods['customsCapitalRegimeIndicator'] = product.l10n_br_customs_regime_id.name

            # the maximum length allowed by the API is 6
            descriptor['unit'] = line_uom.name[:6] if line_uom else ''

            if legal_uom and line_uom:
                descriptor['unitTaxable'] = legal_uom.name[:6]
                descriptor['cbsIbsUnitFactor'] = line_uom._compute_quantity(1, legal_uom)

        return res

    def _l10n_br_update_location_cbs_ibs(self, location, partner):
        location.setdefault('taxesSettings', {}).update({
            'notCbsIbsTaxPayer': not partner.l10n_br_is_cbs_ibs_taxpayer,
        })
        if partner.l10n_br_tax_regime == 'simplified':
            is_normal = partner.l10n_br_is_cbs_ibs_normal
            location.setdefault('taxesSettings', {}).update(
                {
                    'cbsIbsTaxPayer': is_normal,
                    'pCredCBSSN': 0 if is_normal else partner.l10n_br_cbs_credit,
                    'pCredIBSSN': 0 if is_normal else partner.l10n_br_ibs_credit,
                }
            )

    def _l10n_br_get_calculate_payload(self):
        # Override.
        res = super()._l10n_br_get_calculate_payload()
        if not self.company_id.l10n_br_is_icbs:
            return res

        header_for_type = res['header'].setdefault('services' if self.l10n_br_is_service_transaction else 'goods', {})
        header_for_type['enableCalcICBS'] = True  # enables fiscal reform

        if not self.l10n_br_is_service_transaction and (presence := self.l10n_br_presence):
            header_for_type['indPres'] = presence
            if presence in ('2', '3', '9'):
                header_for_type['indIntermed'] = '0'

        locations = res['header']['locations']
        self._l10n_br_update_location_cbs_ibs(locations['establishment'], self.company_id.partner_id)

        entity_partner = self.partner_id
        entity_location = locations['entity']
        self._l10n_br_update_location_cbs_ibs(entity_location, entity_partner)

        if self.l10n_br_is_service_transaction:
            partner_shipping_id = self.partner_shipping_id  # partner_shipping_id doesn't exist on pos.order, but that will never be a service transaction.
            locations.setdefault('rendered', {}).update({
                'name': partner_shipping_id.name or partner_shipping_id.display_name,
                'businessName': partner_shipping_id.name or partner_shipping_id.display_name,
                'type': self._l10n_br_get_partner_type(partner_shipping_id),
                'federalTaxId': partner_shipping_id.vat,
                'address': {
                    'number': partner_shipping_id.street_number,
                    'street': partner_shipping_id.street,
                    'neighborhood': partner_shipping_id.street2,
                    'zipcode': partner_shipping_id.zip,
                    'cityName': partner_shipping_id.city,
                    'state': partner_shipping_id.state_id.code,
                }
            })
            if self.l10n_br_service_operation_indicator:
                res['header'].setdefault('services', {})['indOp'] = self.l10n_br_service_operation_indicator

        if entity_partner.l10n_br_tax_regime == 'individual':
            taxes_settings_entity = entity_location.setdefault('taxesSettings', {})
            taxes_settings_entity['applyCashback'] = entity_partner.l10n_br_is_cashback_applied

        return res
