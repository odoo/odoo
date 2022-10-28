# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """
    NOTES
    1. Fields with name starting with 'pos_' are removed from the vals before super call to `create`.
       Values of these fields are written to `pos_config_id` record after the super call.
       This is done so that these fields are written at the same time to the active pos.config record.
    2. During `creation` of this record, each related field is written to the source record
       *one after the other*, so constraints on the source record that are based on multiple
       fields might not work properly. However, only the *modified* related fields are written
       to the source field. But the identification of modified fields happen during the super
       call, not before `create` is called. Because of this, vals contains a lot of field before
       super call, then the number of fields is reduced after.
    """
    _inherit = 'res.config.settings'

    def _default_pos_config(self):
        # Default to the last modified pos.config.
        active_model = self.env.context.get('active_model', '')
        if active_model == 'pos.config':
            return self.env.context.get('active_id')
        return self.env['pos.config'].search([('company_id', '=', self.env.company.id)], order='write_date desc', limit=1)

    pos_config_id = fields.Many2one('pos.config', string="Point of Sale", default=lambda self: self._default_pos_config())
    sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", related='company_id.account_sale_tax_id', readonly=False)
    module_pos_mercury = fields.Boolean(string="Vantiv Payment Terminal", help="The transactions are processed by Vantiv. Set your Vantiv credentials on the related payment method.")
    module_pos_adyen = fields.Boolean(string="Adyen Payment Terminal", help="The transactions are processed by Adyen. Set your Adyen credentials on the related payment method.")
    module_pos_stripe = fields.Boolean(string="Stripe Payment Terminal", help="The transactions are processed by Stripe. Set your Stripe credentials on the related payment method.")
    module_pos_six = fields.Boolean(string="Six Payment Terminal", help="The transactions are processed by Six. Set the IP address of the terminal on the related payment method.")
    update_stock_quantities = fields.Selection(related="company_id.point_of_sale_update_stock_quantities", readonly=False)
    account_default_pos_receivable_account_id = fields.Many2one(string='Default Account Receivable (PoS)', related='company_id.account_default_pos_receivable_account_id', readonly=False)
    is_default_pricelist_displayed = fields.Boolean(compute="_compute_pos_pricelist_id", compute_sudo=True)
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', related='company_id.nomenclature_id', readonly=False)

    # pos.config fields
    pos_module_pos_discount = fields.Boolean(related='pos_config_id.module_pos_discount', readonly=False)
    pos_module_pos_hr = fields.Boolean(related='pos_config_id.module_pos_hr', readonly=False)
    pos_module_pos_restaurant = fields.Boolean(related='pos_config_id.module_pos_restaurant', readonly=False)

    pos_allowed_pricelist_ids = fields.Many2many('product.pricelist', compute='_compute_pos_allowed_pricelist_ids')
    pos_amount_authorized_diff = fields.Float(related='pos_config_id.amount_authorized_diff', readonly=False)
    pos_available_pricelist_ids = fields.Many2many('product.pricelist', string='Available Pricelists', compute='_compute_pos_pricelist_id', readonly=False, store=True)
    pos_cash_control = fields.Boolean(related='pos_config_id.cash_control')
    pos_cash_rounding = fields.Boolean(related='pos_config_id.cash_rounding', readonly=False, string="Cash Rounding (PoS)")
    pos_company_has_template = fields.Boolean(related='pos_config_id.company_has_template')
    pos_default_bill_ids = fields.Many2many(related='pos_config_id.default_bill_ids', readonly=False)
    pos_default_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position', compute='_compute_pos_fiscal_positions', readonly=False, store=True)
    pos_fiscal_position_ids = fields.Many2many('account.fiscal.position', string='Fiscal Positions', compute='_compute_pos_fiscal_positions', readonly=False, store=True)
    pos_has_active_session = fields.Boolean(related='pos_config_id.has_active_session')
    pos_iface_available_categ_ids = fields.Many2many('pos.category', string='Available PoS Product Categories', compute='_compute_pos_iface_available_categ_ids', readonly=False, store=True)
    pos_iface_big_scrollbars = fields.Boolean(related='pos_config_id.iface_big_scrollbars', readonly=False)
    pos_iface_cashdrawer = fields.Boolean(string='Cashdrawer', compute='_compute_pos_iface_cashdrawer', readonly=False, store=True)
    pos_iface_customer_facing_display_local = fields.Boolean(related='pos_config_id.iface_customer_facing_display_local', readonly=False)
    pos_iface_customer_facing_display_via_proxy = fields.Boolean(string='Customer Facing Display', compute='_compute_pos_iface_customer_facing_display_via_proxy', readonly=False, store=True)
    pos_iface_electronic_scale = fields.Boolean(string='Electronic Scale', compute='_compute_pos_iface_electronic_scale', readonly=False, store=True)
    pos_iface_print_auto = fields.Boolean(related='pos_config_id.iface_print_auto', readonly=False)
    pos_iface_print_skip_screen = fields.Boolean(related='pos_config_id.iface_print_skip_screen', readonly=False)
    pos_iface_print_via_proxy = fields.Boolean(string='Print via Proxy', compute='_compute_pos_iface_print_via_proxy', readonly=False, store=True)
    pos_iface_scan_via_proxy = fields.Boolean(string='Scan via Proxy', compute='_compute_pos_iface_scan_via_proxy', readonly=False, store=True)
    pos_iface_start_categ_id = fields.Many2one('pos.category', string='Initial Category', compute='_compute_pos_iface_start_categ_id', readonly=False, store=True)
    pos_iface_tax_included = fields.Selection(related='pos_config_id.iface_tax_included', readonly=False)
    pos_iface_tipproduct = fields.Boolean(related='pos_config_id.iface_tipproduct', readonly=False)
    pos_invoice_journal_id = fields.Many2one(related='pos_config_id.invoice_journal_id', readonly=False)
    pos_is_header_or_footer = fields.Boolean(related='pos_config_id.is_header_or_footer', readonly=False)
    pos_is_margins_costs_accessible_to_every_user = fields.Boolean(related='pos_config_id.is_margins_costs_accessible_to_every_user', readonly=False)
    pos_is_posbox = fields.Boolean(related='pos_config_id.is_posbox', readonly=False)
    pos_journal_id = fields.Many2one(related='pos_config_id.journal_id', readonly=False)
    pos_limit_categories = fields.Boolean(related='pos_config_id.limit_categories', readonly=False)
    pos_limited_partners_amount = fields.Integer(related='pos_config_id.limited_partners_amount', readonly=False)
    pos_limited_partners_loading = fields.Boolean(related='pos_config_id.limited_partners_loading', readonly=False)
    pos_limited_products_amount = fields.Integer(related='pos_config_id.limited_products_amount', readonly=False)
    pos_limited_products_loading = fields.Boolean(related='pos_config_id.limited_products_loading', readonly=False)
    pos_manual_discount = fields.Boolean(related='pos_config_id.manual_discount', readonly=False)
    pos_only_round_cash_method = fields.Boolean(related='pos_config_id.only_round_cash_method', readonly=False)
    pos_other_devices = fields.Boolean(related='pos_config_id.other_devices', readonly=False)
    pos_partner_load_background = fields.Boolean(related='pos_config_id.partner_load_background', readonly=False)
    pos_payment_method_ids = fields.Many2many(related='pos_config_id.payment_method_ids', readonly=False)
    pos_picking_policy = fields.Selection(related='pos_config_id.picking_policy', readonly=False)
    pos_picking_type_id = fields.Many2one(related='pos_config_id.picking_type_id', readonly=False)
    pos_pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist', compute='_compute_pos_pricelist_id', readonly=False, store=True)
    pos_product_load_background = fields.Boolean(related='pos_config_id.product_load_background', readonly=False)
    pos_proxy_ip = fields.Char(string='IP Address', compute='_compute_pos_proxy_ip', readonly=False, store=True)
    pos_receipt_footer = fields.Text(string='Receipt Footer', compute='_compute_pos_receipt_header_footer', readonly=False, store=True)
    pos_receipt_header = fields.Text(string='Receipt Header', compute='_compute_pos_receipt_header_footer', readonly=False, store=True)
    pos_restrict_price_control = fields.Boolean(related='pos_config_id.restrict_price_control', readonly=False)
    pos_rounding_method = fields.Many2one(related='pos_config_id.rounding_method', readonly=False)
    pos_route_id = fields.Many2one(related='pos_config_id.route_id', readonly=False)
    pos_selectable_categ_ids = fields.Many2many('pos.category', compute='_compute_pos_selectable_categ_ids')
    pos_sequence_id = fields.Many2one(related='pos_config_id.sequence_id')
    pos_set_maximum_difference = fields.Boolean(related='pos_config_id.set_maximum_difference', readonly=False)
    pos_ship_later = fields.Boolean(related='pos_config_id.ship_later', readonly=False)
    pos_start_category = fields.Boolean(related='pos_config_id.start_category', readonly=False)
    pos_tax_regime_selection = fields.Boolean(related='pos_config_id.tax_regime_selection', readonly=False)
    pos_tip_product_id = fields.Many2one('product.product', string='Tip Product', compute='_compute_pos_tip_product_id', readonly=False, store=True)
    pos_use_pricelist = fields.Boolean(related='pos_config_id.use_pricelist', readonly=False)
    pos_warehouse_id = fields.Many2one(related='pos_config_id.warehouse_id', readonly=False, string="Warehouse (PoS)")
    point_of_sale_use_ticket_qr_code = fields.Boolean(related='company_id.point_of_sale_use_ticket_qr_code', readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        # STEP: Remove the 'pos' fields from each vals.
        #   They will be written atomically to `pos_config_id` after the super call.
        pos_config_id_to_fields_vals_map = {}

        for vals in vals_list:
            pos_config_id = vals.get('pos_config_id')
            if pos_config_id:
                pos_fields_vals = {}

                if vals.get('pos_cash_rounding'):
                    vals['group_cash_rounding'] = True

                if vals.get('pos_use_pricelist'):
                    vals['group_product_pricelist'] = True

                for field in self._fields.values():
                    if field.name == 'pos_config_id':
                        continue

                    val = vals.get(field.name)

                    # Add only to pos_fields_vals if
                    #   1. _field is in vals -- meaning, the _field is in view.
                    #   2. _field starts with 'pos_' -- meaning, the _field is a pos field.
                    if field.name.startswith('pos_') and val is not None:
                        pos_config_field_name = field.name[4:]
                        if not pos_config_field_name in self.env['pos.config']._fields:
                            _logger.warning("The value of '%s' is not properly saved to the pos_config_id field because the destination"
                                " field '%s' is not a valid field in the pos.config model.", field.name, pos_config_field_name)
                        else:
                            pos_fields_vals[pos_config_field_name] = val
                            del vals[field.name]

                pos_config_id_to_fields_vals_map[pos_config_id] = pos_fields_vals

        # STEP: Call super on the modified vals_list.
        # NOTE: When creating `res.config.settings` records, it doesn't write on *unmodified* related fields.
        result = super().create(vals_list)

        # STEP: Finally, we write the value of 'pos' fields to 'pos_config_id'.
        for pos_config_id, pos_fields_vals in pos_config_id_to_fields_vals_map.items():
            pos_config = self.env['pos.config'].browse(pos_config_id)
            pos_config.write(pos_fields_vals)

        return result

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if not self.group_product_pricelist:
            self.env['pos.config'].search([
                ('use_pricelist', '=', True)
            ]).use_pricelist = False

        if not self.group_cash_rounding:
            self.env['pos.config'].search([
                ('cash_rounding', '=', True)
            ]).cash_rounding = False

    def action_pos_config_create_new(self):
        return {
            'view_mode': 'form',
            'res_model': 'pos.config',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': False,
            'context': {'pos_config_open_modal': True, 'pos_config_create_mode': True},
        }

    def pos_open_ui(self):
        if self._context.get('pos_config_id'):
            pos_config_id = self._context['pos_config_id']
            pos_config = self.env['pos.config'].browse(pos_config_id)
            return pos_config.open_ui()

    @api.model
    def _is_cashdrawer_displayed(self, res_config):
        return res_config.pos_iface_print_via_proxy

    @api.depends('pos_limit_categories', 'pos_config_id')
    def _compute_pos_iface_available_categ_ids(self):
        for res_config in self:
            if not res_config.pos_limit_categories:
                res_config.pos_iface_available_categ_ids = False
            else:
                res_config.pos_iface_available_categ_ids = res_config.pos_config_id.iface_available_categ_ids

    @api.depends('pos_start_category', 'pos_config_id')
    def _compute_pos_iface_start_categ_id(self):
        for res_config in self:
            if not res_config.pos_start_category:
                res_config.pos_iface_start_categ_id = False
            else:
                res_config.pos_iface_start_categ_id = res_config.pos_config_id.iface_start_categ_id

    @api.depends('pos_iface_available_categ_ids')
    def _compute_pos_selectable_categ_ids(self):
        for res_config in self:
            if res_config.pos_iface_available_categ_ids:
                res_config.pos_selectable_categ_ids = res_config.pos_iface_available_categ_ids
            else:
                res_config.pos_selectable_categ_ids = self.env['pos.category'].search([])

    @api.depends('pos_iface_print_via_proxy', 'pos_config_id')
    def _compute_pos_iface_cashdrawer(self):
        for res_config in self:
            if self._is_cashdrawer_displayed(res_config):
                res_config.pos_iface_cashdrawer = res_config.pos_config_id.iface_cashdrawer
            else:
                res_config.pos_iface_cashdrawer = False

    @api.depends('pos_is_header_or_footer', 'pos_config_id')
    def _compute_pos_receipt_header_footer(self):
        for res_config in self:
            if res_config.pos_is_header_or_footer:
                res_config.pos_receipt_header = res_config.pos_config_id.receipt_header
                res_config.pos_receipt_footer = res_config.pos_config_id.receipt_footer
            else:
                res_config.pos_receipt_header = False
                res_config.pos_receipt_footer = False

    @api.depends('pos_tax_regime_selection', 'pos_config_id')
    def _compute_pos_fiscal_positions(self):
        for res_config in self:
            if res_config.pos_tax_regime_selection:
                res_config.pos_default_fiscal_position_id = res_config.pos_config_id.default_fiscal_position_id
                res_config.pos_fiscal_position_ids = res_config.pos_config_id.fiscal_position_ids
            else:
                res_config.pos_default_fiscal_position_id = False
                res_config.pos_fiscal_position_ids = [(5, 0, 0)]

    @api.depends('pos_iface_tipproduct', 'pos_config_id')
    def _compute_pos_tip_product_id(self):
        for res_config in self:
            if res_config.pos_iface_tipproduct:
                res_config.pos_tip_product_id = res_config.pos_config_id.tip_product_id
            else:
                res_config.pos_tip_product_id = False

    @api.depends('pos_use_pricelist', 'pos_config_id', 'pos_journal_id')
    def _compute_pos_pricelist_id(self):
        for res_config in self:
            currency_id = res_config.pos_journal_id.currency_id.id if res_config.pos_journal_id.currency_id else res_config.pos_config_id.company_id.currency_id.id
            pricelists_in_current_currency = self.env['product.pricelist'].search([('company_id', 'in', (False, res_config.pos_config_id.company_id.id)), ('currency_id', '=', currency_id)])
            if not res_config.pos_use_pricelist:
                res_config.pos_available_pricelist_ids = pricelists_in_current_currency[:1]
                res_config.pos_pricelist_id = pricelists_in_current_currency[:1]
            else:
                if any([p.currency_id.id != currency_id for p in res_config.pos_available_pricelist_ids]):
                    res_config.pos_available_pricelist_ids = pricelists_in_current_currency
                    res_config.pos_pricelist_id = pricelists_in_current_currency[:1]
                else:
                    res_config.pos_available_pricelist_ids = res_config.pos_config_id.available_pricelist_ids
                    res_config.pos_pricelist_id = res_config.pos_config_id.pricelist_id

            # TODO: Remove this field in master because it's always True.
            res_config.is_default_pricelist_displayed = True

    @api.depends('pos_available_pricelist_ids', 'pos_use_pricelist')
    def _compute_pos_allowed_pricelist_ids(self):
        for res_config in self:
            if res_config.pos_use_pricelist:
                res_config.pos_allowed_pricelist_ids = res_config.pos_available_pricelist_ids.ids
            else:
                res_config.pos_allowed_pricelist_ids = self.env['product.pricelist'].search([]).ids

    @api.depends('pos_is_posbox', 'pos_config_id')
    def _compute_pos_proxy_ip(self):
        for res_config in self:
            if not res_config.pos_is_posbox:
                res_config.pos_proxy_ip = False
            else:
                res_config.pos_proxy_ip = res_config.pos_config_id.proxy_ip

    @api.depends('pos_is_posbox', 'pos_config_id')
    def _compute_pos_iface_print_via_proxy(self):
        for res_config in self:
            if not res_config.pos_is_posbox:
                res_config.pos_iface_print_via_proxy = False
            else:
                res_config.pos_iface_print_via_proxy = res_config.pos_config_id.iface_print_via_proxy

    @api.depends('pos_is_posbox', 'pos_config_id')
    def _compute_pos_iface_scan_via_proxy(self):
        for res_config in self:
            if not res_config.pos_is_posbox:
                res_config.pos_iface_scan_via_proxy = False
            else:
                res_config.pos_iface_scan_via_proxy = res_config.pos_config_id.iface_scan_via_proxy

    @api.depends('pos_is_posbox', 'pos_config_id')
    def _compute_pos_iface_electronic_scale(self):
        for res_config in self:
            if not res_config.pos_is_posbox:
                res_config.pos_iface_electronic_scale = False
            else:
                res_config.pos_iface_electronic_scale = res_config.pos_config_id.iface_electronic_scale

    @api.depends('pos_is_posbox', 'pos_config_id')
    def _compute_pos_iface_customer_facing_display_via_proxy(self):
        for res_config in self:
            if not res_config.pos_is_posbox:
                res_config.pos_iface_customer_facing_display_via_proxy = False
            else:
                res_config.pos_iface_customer_facing_display_via_proxy = res_config.pos_config_id.iface_customer_facing_display_via_proxy
