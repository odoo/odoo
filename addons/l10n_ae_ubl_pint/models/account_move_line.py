from odoo import api, fields, models

from odoo.addons.l10n_ae_ubl_pint.models.product_template import L10N_AE_GOODS_SERVICE_TYPE_SELECTION

L10N_AE_ITEM_FIELDS = (
    'l10n_ae_item_type',
    'l10n_ae_goods_service_type',
    'l10n_ae_hs_code',
    'l10n_ae_service_accounting_code',
)


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'l10n.ae.pint.check.mixin']

    # Item data (BTAE-13, IBT-158, BTAE-17, goods type) taken from the product but kept per line,
    # which is what the export reads. https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/codelist/ItemType/
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
        """ Follow the product while the invoice is a draft, like l10n_in's HSN/SAC code.

        Otherwise keep the current values: an unassigned stored compute would reset them to False.
        """
        for line in self:
            product = line.product_id
            if product and line.display_type == 'product' and line.move_id.country_code == 'AE' and line.parent_state == 'draft':
                values = product._l10n_ae_pint_get_item_values()
            else:
                values = {fname: line[fname] for fname in L10N_AE_ITEM_FIELDS}
            line.update(values)

    def _l10n_ae_pint_group_by_error_code(self):
        """ ibr-184-ae/185/186: Goods need an HS code, Services a service accounting code, Both
        one of each. Without an item type (BTAE-13 is 0..1), nothing is required.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-186-ae/
        """
        self.ensure_one()
        if self.display_type != 'product':
            return False
        if self.l10n_ae_item_type in ('G', 'B') and not self.l10n_ae_hs_code:
            return (
                ("message", self.env._("Invoice line(s) for goods should have their HS Code set.")),
                ("error_code", "l10n_ae_pint_line_classification_code_missing"),
                ("level", "danger"),
            )
        if self.l10n_ae_item_type in ('S', 'B') and not self.l10n_ae_service_accounting_code:
            return (
                ("message", self.env._("Invoice line(s) for services should have their Service Accounting Code set.")),
                ("error_code", "l10n_ae_pint_line_service_accounting_code_missing"),
                ("level", "danger"),
            )
        return False

    def _l10n_ae_pint_get_alert_records(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.move_id

    def _l10n_ae_pint_action_text(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.env._("View Invoice(s)")
