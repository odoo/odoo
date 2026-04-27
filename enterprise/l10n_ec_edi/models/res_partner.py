# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_ec.models.res_partner import PartnerIdTypeEc
from odoo.addons.l10n_ec.models.res_partner import verify_final_consumer


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ec_taxpayer_type_id = fields.Many2one(
        comodel_name='l10n_ec.taxpayer.type',
        string="SRI Taxpayer Type",
        help="Ecuador: Select the partner position in the tax pyramid, to automate the computation of VAT withholdings."
    )
    l10n_ec_related_party = fields.Boolean(
        string="Related Party",
        help="Ecuador: Select the option if the partner is a related party. Related parties are other companies or "
             "persons that participate directly or indirectly in the management, administration, control or capital "
             "of your company. An example of a related part might be a shareholder of the company."
    )

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + ['l10n_ec_taxpayer_type_id', 'l10n_ec_related_party']

    def _get_sri_code_for_partner(self):
        """
        Returns ID code for edi documents, based on table 6 of SRI's electronic documents specification.
        """
        partner_id_type = self._l10n_ec_get_identification_type()
        if verify_final_consumer(self.vat):  # checks that all 13 digits are 9
            return PartnerIdTypeEc.FINAL_CONSUMER
        elif partner_id_type == 'foreign':
            return PartnerIdTypeEc.FOREIGN
        else:
            # Otherwise the EDI code corresponds to the one for out moves
            return PartnerIdTypeEc.get_ats_code_for_partner(self, 'out_')

    def _get_l10n_ec_edi_supplier_identification_type_code(self):
        # For the withhold xml in Ecuador, the provider type is identified as a company or a natural person
        # when the third digit of its identification is 6 or 9
        if not self.vat:
            return None
        supplier_code = '01'
        if self.vat[2] in ['6', '9']:
            supplier_code = '02'
        return supplier_code
