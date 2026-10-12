# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.addons.l10n_kr.models.res_partner import L10N_KR_ISSUANCE_TYPES


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_kr_issuance_type = fields.Selection(
        selection=L10N_KR_ISSUANCE_TYPES,
        string="Proof of Issuance",
        compute='_compute_l10n_kr_issuance_type',
        store=True,
        readonly=False,
        init_storage=lambda model: None,
        help="South Korean government-verified proof of issuance used to legally justify this transaction. "
             "Propagated to the customer invoice when it is created.",
    )

    @api.depends('partner_id.commercial_partner_id', 'country_code')
    def _compute_l10n_kr_issuance_type(self):
        for order in self:
            if order.country_code == 'KR':
                order.l10n_kr_issuance_type = order.partner_id.commercial_partner_id.l10n_kr_default_issuance_type
            else:
                order.l10n_kr_issuance_type = False

    def _get_invoice_grouping_keys(self):
        # EXTENDS 'sale' - orders classified under different proofs of issuance are reported
        # under different VAT boxes, so they must not be merged into a single invoice.
        return super()._get_invoice_grouping_keys() + ['l10n_kr_issuance_type']

    def _prepare_invoice(self):
        # EXTENDS 'sale'
        values = super()._prepare_invoice()
        if self.company_id.account_fiscal_country_id.code == 'KR':
            values['l10n_kr_issuance_type'] = self.l10n_kr_issuance_type
        return values
