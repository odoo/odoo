from odoo import api, fields, models
from odoo.tools import frozendict

from odoo.addons.l10n_ae_ubl_pint.models.product_template import L10N_AE_GOODS_SERVICE_TYPE_SELECTION


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_ae_item_type = fields.Selection(
        string='Item Type',
        selection=[
            ('G', 'Goods'),
            ('S', 'Services'),
            ('B', 'Both'),
        ],
        compute='_compute_l10n_ae_item_values',
        store=True,
        readonly=False,
        precompute=True,
    )
    l10n_ae_goods_service_type = fields.Selection(
        string='RCM Goods Type',
        selection=L10N_AE_GOODS_SERVICE_TYPE_SELECTION,
        compute='_compute_l10n_ae_item_values',
        store=True,
        readonly=False,
        precompute=True,
    )
    l10n_ae_hs_code = fields.Char(
        string='HS Code',
        compute='_compute_l10n_ae_item_values',
        store=True,
        readonly=False,
        precompute=True,
    )
    l10n_ae_service_accounting_code = fields.Char(
        string='Service Accounting Code',
        compute='_compute_l10n_ae_item_values',
        store=True,
        readonly=False,
        precompute=True,
    )

    @api.depends(
        'product_id',
        'product_id.l10n_ae_is_good_and_service',
        'product_id.l10n_ae_goods_service_type',
        'product_id.l10n_ae_hs_code',
        'product_id.l10n_ae_service_accounting_code',
    )
    def _compute_l10n_ae_item_values(self):
        """ Follow the product while the invoice is a draft, like l10n_in's HSN/SAC code. """
        for line in self:
            product = line.product_id
            if product and line.display_type == 'product' and line.move_id.country_code == 'AE' and line.parent_state == 'draft':
                line.update({
                    'l10n_ae_item_type': product._l10n_ae_pint_get_item_type(),
                    'l10n_ae_goods_service_type': product.l10n_ae_goods_service_type,
                    'l10n_ae_hs_code': product.l10n_ae_hs_code,
                    'l10n_ae_service_accounting_code': product.l10n_ae_service_accounting_code,
                })

    def _l10n_ae_pint_get_errors(self):
        """ ibr-184-ae/185/186: Goods need an HS code, Services a service accounting code, Both
        one of each. Without an item type (BTAE-13 is 0..1), nothing is required.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-186-ae/
        """
        self.ensure_one()
        errors = []
        if self.display_type != 'product':
            return []
        if self.l10n_ae_item_type in ('G', 'B') and not self.l10n_ae_hs_code:
            errors.append(frozendict({
                'message': self.env._("Invoice line(s) for goods should have their HS Code set."),
                'error_code': 'l10n_ae_pint_line_classification_code_missing',
                'level': 'danger',
            }))
        if self.l10n_ae_item_type in ('S', 'B') and not self.l10n_ae_service_accounting_code:
            errors.append(frozendict({
                'message': self.env._("Invoice line(s) for services should have their Service Accounting Code set."),
                'error_code': 'l10n_ae_pint_line_service_accounting_code_missing',
                'level': 'danger',
            }))
        return errors
