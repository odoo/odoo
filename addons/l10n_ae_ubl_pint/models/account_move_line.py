from odoo import api, fields, models

from odoo.addons.l10n_ae_ubl_pint.models.product_product import L10N_AE_GOODS_SERVICE_TYPE_SELECTION


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'l10n.ae.pint.check.mixin']

    # The PINT AE item data (BTAE-13, IBT-158, BTAE-17 and the goods type) is taken from the
    # product but kept on the line, so it can be set on a line without a product and adjusted per
    # line. The exporter only reads these fields, never the product's.
    # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-13/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/codelist/ItemType/
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
    )
    l10n_ae_goods_service_type = fields.Selection(
        string='Goods and Service Type',
        selection=L10N_AE_GOODS_SERVICE_TYPE_SELECTION,
        compute='_compute_l10n_ae_item_values',
        store=True,
        readonly=False,
    )
    l10n_ae_classification_code = fields.Char(
        string='HS Code',
        compute='_compute_l10n_ae_item_values',
        store=True,
        readonly=False,
    )
    l10n_ae_service_accounting_code = fields.Char(
        string='Service Accounting Code',
        compute='_compute_l10n_ae_item_values',
        store=True,
        readonly=False,
    )

    @api.depends('product_id')
    def _compute_l10n_ae_item_values(self):
        for line in self:
            product = line.product_id
            if not product or line.display_type != 'product' or line.move_id.country_code != 'AE':
                # Keep what was set by hand on a line without a product.
                line.l10n_ae_item_type = line.l10n_ae_item_type
                line.l10n_ae_goods_service_type = line.l10n_ae_goods_service_type
                line.l10n_ae_classification_code = line.l10n_ae_classification_code
                line.l10n_ae_service_accounting_code = line.l10n_ae_service_accounting_code
                continue
            line.l10n_ae_item_type = product._l10n_ae_pint_get_item_type()
            line.l10n_ae_goods_service_type = product.l10n_ae_goods_service_type
            line.l10n_ae_classification_code = product.l10n_ae_classification_code
            line.l10n_ae_service_accounting_code = product.l10n_ae_service_accounting_code

    def _l10n_ae_pint_group_by_error_code(self):
        self.ensure_one()
        # A global discount line is exported as a document level allowance, not as an item.
        if self.display_type != 'product' or self._l10n_ae_is_global_discount():
            return False
        if not self.l10n_ae_item_type:
            return (
                ("message", self.env._("Invoice line(s) should have their Item Type set.")),
                ("error_code", "l10n_ae_pint_line_item_type_missing"),
                ("level", "danger"),
            )
        # ibr-184-ae/ibr-185-ae/ibr-186-ae: an item of type Goods needs the classification
        # identifier, Services needs the service accounting code, and Both needs one of each.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-184-ae/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-185-ae/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-186-ae/
        if self.l10n_ae_item_type in ('G', 'B') and not self.l10n_ae_classification_code:
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

    def _l10n_ae_is_global_discount(self):
        """Same test as account.move's _prepare_product_base_line_for_taxes_computation."""
        self.ensure_one()
        return (self.extra_tax_data or {}).get('computation_key', '').startswith('global_discount')

    def _l10n_ae_pint_get_alert_records(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.move_id

    def _l10n_ae_pint_action_text(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.env._("View Invoice(s)")
