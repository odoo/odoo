# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from uuid import uuid4
import pytz

from odoo import api, fields, models, _, Command
from odoo.http import request
from odoo.osv.expression import OR, AND
from odoo.exceptions import AccessError, ValidationError, UserError


class PosConfig(models.Model):
    _name = 'pos.config'
    _description = 'Point of Sale Configuration'
    _check_company_auto = True

    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1).id

    def _default_picking_type_id(self):
        return self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1).pos_type_id.id

    def _default_sale_journal(self):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', 'in', ('sale', 'general')),
            ('code', '=', 'POSS'),
        ], limit=1)

    def _default_invoice_journal(self):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'sale'),
        ], limit=1)

    def _default_payment_methods(self):
        """ Should only default to payment methods that are compatible to this config's company and currency.
        """
        domain = [
            *self.env['pos.payment.method']._check_company_domain(self.env.company),
            ('split_transactions', '=', False),
            '|',
                ('journal_id', '=', False),
                ('journal_id.currency_id', 'in', (False, self.env.company.currency_id.id)),
        ]
        non_cash_pm = self.env['pos.payment.method'].search(domain + [('is_cash_count', '=', False)])
        available_cash_pm = self.env['pos.payment.method'].search(domain + [('is_cash_count', '=', True),
                                                                            ('config_ids', '=', False)], limit=1)
        return non_cash_pm | available_cash_pm

    def _get_group_pos_manager(self):
        return self.env.ref('point_of_sale.group_pos_manager')

    def _get_group_pos_user(self):
        return self.env.ref('point_of_sale.group_pos_user')

    def _get_default_tip_product(self):
        tip_product_id = self.env.ref("point_of_sale.product_product_tip", raise_if_not_found=False)
        if not tip_product_id:
            tip_product_id = self.env['product.product'].search([('default_code', '=', 'TIPS')], limit=1)
        return tip_product_id

    name = fields.Char(string='Point of Sale', required=True, help="An internal identification of the point of sale.")
    printer_ids = fields.Many2many('pos.printer', 'pos_config_printer_rel', 'config_id', 'printer_id', string='Order Printers')
    is_order_printer = fields.Boolean('Order Printer')
    is_installed_account_accountant = fields.Boolean(string="Is the Full Accounting Installed",
        compute="_compute_is_installed_account_accountant")
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
        default=_default_picking_type_id,
        required=True,
        domain="[('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)]",
        ondelete='restrict')
    journal_id = fields.Many2one(
        'account.journal', string='Point of Sale Journal',
        domain=[('type', 'in', ('general', 'sale'))],
        check_company=True,
        help="Accounting journal used to post POS session journal entries and POS invoice payments.",
        default=_default_sale_journal,
        ondelete='restrict')
    invoice_journal_id = fields.Many2one(
        'account.journal', string='Invoice Journal',
        check_company=True,
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to create invoices.",
        default=_default_invoice_journal)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', compute_sudo=True, string="Currency")
    iface_cashdrawer = fields.Boolean(string='Cashdrawer', help="Automatically open the cashdrawer.")
    iface_electronic_scale = fields.Boolean(string='Electronic Scale', help="Enables Electronic Scale integration.")
    iface_customer_facing_display = fields.Boolean(compute='_compute_customer_facing_display')
    iface_customer_facing_display_via_proxy = fields.Boolean(string='Customer Facing Display', help="Show checkout to customers with a remotely-connected screen.")
    iface_customer_facing_display_local = fields.Boolean(string='Local Customer Facing Display', help="Show checkout to customers.")
    iface_customer_facing_display_background_image_1920 = fields.Image(string='Background Image', max_width=1920, max_height=1920, compute='_compute_iface_customer_facing_display_background_image_1920', store=True)
    iface_print_via_proxy = fields.Boolean(string='Print via Proxy', help="Bypass browser printing and prints via the hardware proxy.")
    iface_scan_via_proxy = fields.Boolean(string='Scan via Proxy', help="Enable barcode scanning with a remotely connected barcode scanner and card swiping with a Vantiv card reader.")
    iface_big_scrollbars = fields.Boolean('Large Scrollbars', help='For imprecise industrial touchscreens.')
    iface_print_auto = fields.Boolean(string='Automatic Receipt Printing', default=False,
        help='The receipt will automatically be printed at the end of each order.')
    iface_print_skip_screen = fields.Boolean(string='Skip Preview Screen', default=True,
        help='The receipt screen will be skipped if the receipt can be printed automatically.')
    iface_tax_included = fields.Selection([('subtotal', 'Tax-Excluded Price'), ('total', 'Tax-Included Price')], string="Tax Display", default='total', required=True)
    iface_start_categ_id = fields.Many2one('pos.category', string='Initial Category',
        help='The point of sale will display this product category by default. If no category is specified, all available products will be shown.')
    iface_available_categ_ids = fields.Many2many('pos.category', string='Available PoS Product Categories',
        help='The point of sale will only display products which are within one of the selected category trees. If no category is specified, all available products will be shown')
    restrict_price_control = fields.Boolean(string='Restrict Price Modifications to Managers',
        help="Only users with Manager access rights for PoS app can modify the product prices on orders.")
    is_margins_costs_accessible_to_every_user = fields.Boolean(string='Margins & Costs', default=False,
        help='When disabled, only PoS manager can view the margin and cost of product among the Product info.')
    cash_control = fields.Boolean(string='Advanced Cash Control', compute='_compute_cash_control', help="Check the amount of the cashbox at opening and closing.")
    set_maximum_difference = fields.Boolean('Set Maximum Difference', help="Set a maximum difference allowed between the expected and counted money during the closing of the session.")
    receipt_header = fields.Text(string='Receipt Header', help="A short text that will be inserted as a header in the printed receipt.")
    receipt_footer = fields.Text(string='Receipt Footer', help="A short text that will be inserted as a footer in the printed receipt.")
    proxy_ip = fields.Char(string='IP Address', size=45,
        help='The hostname or ip address of the hardware proxy, Will be autodetected if left empty.')
    active = fields.Boolean(default=True)
    uuid = fields.Char(readonly=True, default=lambda self: str(uuid4()), copy=False,
        help='A globally unique identifier for this pos configuration, used to prevent conflicts in client-generated data.')
    sequence_id = fields.Many2one('ir.sequence', string='Order IDs Sequence', readonly=True,
        help="This sequence is automatically created by Odoo but you can change it "
        "to customize the reference numbers of your orders.", copy=False, ondelete='restrict')
    sequence_line_id = fields.Many2one('ir.sequence', string='Order Line IDs Sequence', readonly=True,
        help="This sequence is automatically created by Odoo but you can change it "
        "to customize the reference numbers of your orders lines.", copy=False)
    session_ids = fields.One2many('pos.session', 'config_id', string='Sessions')
    current_session_id = fields.Many2one('pos.session', compute='_compute_current_session', string="Current Session")
    current_session_state = fields.Char(compute='_compute_current_session')
    number_of_rescue_session = fields.Integer(string="Number of Rescue Session", compute='_compute_current_session')
    last_session_closing_cash = fields.Float(compute='_compute_last_session')
    last_session_closing_date = fields.Date(compute='_compute_last_session')
    pos_session_username = fields.Char(compute='_compute_current_session_user')
    pos_session_state = fields.Char(compute='_compute_current_session_user')
    pos_session_duration = fields.Char(compute='_compute_current_session_user')
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist',
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured if any.")
    available_pricelist_ids = fields.Many2many('product.pricelist', string='Available Pricelists',
        help="Make several pricelists available in the Point of Sale. You can also apply a pricelist to specific customers from their contact form (in Sales tab). To be valid, this pricelist must be listed here as an available pricelist. Otherwise the default pricelist will apply.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    group_pos_manager_id = fields.Many2one('res.groups', string='Point of Sale Manager Group', default=_get_group_pos_manager,
        help='This field is there to pass the id of the pos manager group to the point of sale client.')
    group_pos_user_id = fields.Many2one('res.groups', string='Point of Sale User Group', default=_get_group_pos_user,
        help='This field is there to pass the id of the pos user group to the point of sale client.')
    iface_tipproduct = fields.Boolean(string="Product tips")
    tip_product_id = fields.Many2one('product.product', string='Tip Product', default=_get_default_tip_product, help="This product is used as reference on customer receipts.")
    fiscal_position_ids = fields.Many2many('account.fiscal.position', string='Fiscal Positions', help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.')
    default_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position')
    default_bill_ids = fields.Many2many('pos.bill', string="Coins/Bills")
    use_pricelist = fields.Boolean("Use a pricelist.")
    tax_regime_selection = fields.Boolean("Tax Regime Selection value")
    start_category = fields.Boolean("Start Category", default=False)
    limit_categories = fields.Boolean("Restrict Categories")
    module_pos_restaurant = fields.Boolean("Is a Bar/Restaurant")
    module_pos_discount = fields.Boolean("Global Discounts")
    module_pos_mercury = fields.Boolean(string="Integrated Card Payments")
    is_posbox = fields.Boolean("PosBox")
    is_header_or_footer = fields.Boolean("Custom Header & Footer")
    module_pos_hr = fields.Boolean(help="Show employee login screen")
    amount_authorized_diff = fields.Float('Amount Authorized Difference',
        help="This field depicts the maximum difference allowed between the ending balance and the theoretical cash when "
             "closing a session, for non-POS managers. If this maximum is reached, the user will have an error message at "
             "the closing of his session saying that he needs to contact his manager.")
    payment_method_ids = fields.Many2many('pos.payment.method', string='Payment Methods', default=lambda self: self._default_payment_methods(), copy=False)
    company_has_template = fields.Boolean(string="Company has chart of accounts", compute="_compute_company_has_template")
    current_user_id = fields.Many2one('res.users', string='Current Session Responsible', compute='_compute_current_session_user')
    other_devices = fields.Boolean(string="Other Devices", help="Connect devices to your PoS without an IoT Box.")
    rounding_method = fields.Many2one('account.cash.rounding', string="Cash rounding")
    cash_rounding = fields.Boolean(string="Cash Rounding")
    only_round_cash_method = fields.Boolean(string="Only apply rounding on cash")
    has_active_session = fields.Boolean(compute='_compute_current_session')
    manual_discount = fields.Boolean(string="Line Discounts", default=True)
    ship_later = fields.Boolean(string="Ship Later")
    warehouse_id = fields.Many2one('stock.warehouse', default=_default_warehouse_id, ondelete='restrict')
    route_id = fields.Many2one('stock.route', string="Spefic route for products delivered later.")
    picking_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready')],
        string='Shipping Policy', required=True, default='direct',
        help="If you deliver all products at once, the delivery order will be scheduled based on the greatest "
        "product lead time. Otherwise, it will be based on the shortest.")
    auto_validate_terminal_payment = fields.Boolean(default=True, help="Automatically validates orders paid with a payment terminal.")
    trusted_config_ids = fields.Many2many("pos.config", relation="pos_config_trust_relation", column1="is_trusting",
                                          column2="is_trusted", string="Trusted Point of Sale Configurations",
                                          domain="[('id', '!=', pos_config_id), ('module_pos_restaurant', '=', False), ('company_id', '=', company_id)]")

    @api.depends('payment_method_ids')
    def _compute_cash_control(self):
        for config in self:
            config.cash_control = bool(config.payment_method_ids.filtered('is_cash_count'))

    @api.depends('company_id')
    def _compute_company_has_template(self):
        for config in self:
            config.company_has_template = config.company_id.root_id.sudo()._existing_accounting() or config.company_id.chart_template

    def _compute_is_installed_account_accountant(self):
        account_accountant = self.env['ir.module.module'].sudo().search([('name', '=', 'account_accountant'), ('state', '=', 'installed')])
        for pos_config in self:
            pos_config.is_installed_account_accountant = account_accountant and account_accountant.id

    @api.depends('journal_id.currency_id', 'journal_id.company_id.currency_id', 'company_id', 'company_id.currency_id')
    def _compute_currency(self):
        for pos_config in self:
            if pos_config.journal_id:
                pos_config.currency_id = pos_config.journal_id.currency_id.id or pos_config.journal_id.company_id.sudo().currency_id.id
            else:
                pos_config.currency_id = pos_config.company_id.sudo().currency_id.id

    @api.depends('session_ids', 'session_ids.state')
    def _compute_current_session(self):
        """If there is an open session, store it to current_session_id / current_session_State.
        """
        self.session_ids.fetch(["state"])
        for pos_config in self:
            opened_sessions = pos_config.session_ids.filtered(lambda s: s.state != 'closed')
            rescue_sessions = opened_sessions.filtered('rescue')
            session = pos_config.session_ids.filtered(lambda s: s.state != 'closed' and not s.rescue)
            # sessions ordered by id desc
            pos_config.has_active_session = opened_sessions and True or False
            pos_config.current_session_id = session and session[0].id or False
            pos_config.current_session_state = session and session[0].state or False
            pos_config.number_of_rescue_session = len(rescue_sessions)

    @api.depends('session_ids')
    def _compute_last_session(self):
        PosSession = self.env['pos.session']
        for pos_config in self:
            session = PosSession.search_read(
                [('config_id', '=', pos_config.id), ('state', '=', 'closed')],
                ['cash_register_balance_end_real', 'stop_at'],
                order="stop_at desc", limit=1)
            if session:
                timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
                pos_config.last_session_closing_date = session[0]['stop_at'].astimezone(timezone).date()
                pos_config.last_session_closing_cash = session[0]['cash_register_balance_end_real']
            else:
                pos_config.last_session_closing_cash = 0
                pos_config.last_session_closing_date = False

    @api.depends('session_ids')
    def _compute_current_session_user(self):
        for pos_config in self:
            session = pos_config.session_ids.filtered(lambda s: s.state in ['opening_control', 'opened', 'closing_control'] and not s.rescue)
            if session:
                pos_config.pos_session_username = session[0].user_id.sudo().name
                pos_config.pos_session_state = session[0].state
                pos_config.pos_session_duration = (
                    datetime.now() - session[0].start_at
                ).days if session[0].start_at else 0
                pos_config.current_user_id = session[0].user_id
            else:
                pos_config.pos_session_username = False
                pos_config.pos_session_state = False
                pos_config.pos_session_duration = 0
                pos_config.current_user_id = False

    @api.depends('iface_customer_facing_display_via_proxy', 'iface_customer_facing_display_local')
    def _compute_customer_facing_display(self):
        for config in self:
            config.iface_customer_facing_display = config.iface_customer_facing_display_via_proxy or config.iface_customer_facing_display_local

    @api.depends('iface_customer_facing_display')
    def _compute_iface_customer_facing_display_background_image_1920(self):
        for config in self:
            if not config.iface_customer_facing_display:
                config.iface_customer_facing_display_background_image_1920 = False

    @api.constrains('rounding_method')
    def _check_rounding_method_strategy(self):
        for config in self:
            if config.cash_rounding and config.rounding_method.strategy != 'add_invoice_line':
                selection_value = "Add a rounding line"
                for key, val in self.env["account.cash.rounding"]._fields["strategy"]._description_selection(config.env):
                    if key == "add_invoice_line":
                        selection_value = val
                        break
                raise ValidationError(_(
                    "The cash rounding strategy of the point of sale %(pos)s must be: '%(value)s'",
                    pos=config.name,
                    value=selection_value,
                ))

    def _check_profit_loss_cash_journal(self):
        if self.cash_control and self.payment_method_ids:
            for method in self.payment_method_ids:
                if method.is_cash_count and (not method.journal_id.loss_account_id or not method.journal_id.profit_account_id):
                    raise ValidationError(_("You need a loss and profit account on your cash journal."))

    @api.constrains('company_id', 'payment_method_ids')
    def _check_company_payment(self):
        for config in self:
            if self.env['pos.payment.method'].search_count([('id', 'in', config.payment_method_ids.ids), ('company_id', '!=', config.company_id.id)]):
                raise ValidationError(_("The payment methods for the point of sale %s must belong to its company.", self.name))

    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id', 'payment_method_ids')
    def _check_currencies(self):
        for config in self:
            if config.use_pricelist and config.pricelist_id and config.pricelist_id not in config.available_pricelist_ids:
                raise ValidationError(_("The default pricelist must be included in the available pricelists."))

            # Check if the config's payment methods are compatible with its currency
            for pm in config.payment_method_ids:
                if pm.journal_id and pm.journal_id.currency_id and pm.journal_id.currency_id != config.currency_id:
                    raise ValidationError(_("All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))

            if config.use_pricelist and any(config.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != config.currency_id)):
                raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                        " as the Sales Journal set on this point of sale if you use"
                                        " the Accounting application."))
            if config.invoice_journal_id.currency_id and config.invoice_journal_id.currency_id != config.currency_id:
                raise ValidationError(_("The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))

    @api.constrains('iface_start_categ_id', 'iface_available_categ_ids')
    def _check_start_categ(self):
        for config in self:
            allowed_categ_ids = config.iface_available_categ_ids or self.env['pos.category'].search([])
            if config.iface_start_categ_id and config.iface_start_categ_id not in allowed_categ_ids:
                raise ValidationError(_("Start category should belong in the available categories."))

    def _check_payment_method_ids(self):
        self.ensure_one()
        if not self.payment_method_ids:
            raise ValidationError(
                _("You must have at least one payment method configured to launch a session.")
            )

    @api.constrains('pricelist_id', 'available_pricelist_ids')
    def _check_pricelists(self):
        self._check_companies()
        self = self.sudo()
        if self.pricelist_id.company_id and self.pricelist_id.company_id != self.company_id:
            raise ValidationError(
                _("The default pricelist must belong to no company or the company of the point of sale."))

    @api.constrains('company_id', 'available_pricelist_ids')
    def _check_companies(self):
        for config in self:
            if any(pricelist.company_id.id not in [False, config.company_id.id] for pricelist in config.available_pricelist_ids):
                raise ValidationError(_("The selected pricelists must belong to no company or the company of the point of sale."))

    def _check_company_has_template(self):
        self.ensure_one()
        if not self.company_has_template:
            raise ValidationError(_("No chart of account configured, go to the \"configuration / settings\" menu, and "
                                    "install one from the Invoicing tab."))

    @api.constrains('payment_method_ids')
    def _check_payment_method_ids_journal(self):
        for cash_method in self.payment_method_ids.filtered(lambda m: m.journal_id.type == 'cash'):
            if self.env['pos.config'].search([('id', '!=', self.id), ('payment_method_ids', 'in', cash_method.ids)]):
                raise ValidationError(_("This cash payment method is already used in another Point of Sale.\n"
                                        "A new cash payment method should be created for this Point of Sale."))
            if len(cash_method.journal_id.pos_payment_method_ids) > 1:
                raise ValidationError(_("You cannot use the same journal on multiples cash payment methods."))

    @api.constrains('trusted_config_ids')
    def _check_trusted_config_ids_currency(self):
        for config in self:
            for trusted_config in config.trusted_config_ids:
                if trusted_config.currency_id != config.currency_id:
                    raise ValidationError(_("You cannot share open orders with configuration that does not use the same currency."))

    def _compute_display_name(self):
        for config in self:
            last_session = self.env['pos.session'].search([('config_id', '=', config.id)], limit=1)
            if (not last_session) or (last_session.state == 'closed'):
                config.display_name = _("%(pos_name)s (not used)", pos_name=config.name)
            else:
                config.display_name = f"{config.name} ({last_session.user_id.name})"

    def _check_header_footer(self, values):
        if not self.env.is_admin() and {'is_header_or_footer', 'receipt_header', 'receipt_footer'} & values.keys():
            raise AccessError(_('Only administrators can edit receipt headers and footers'))

    def _config_sequence_implementation(self):
        return 'standard'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_header_footer(vals)
            IrSequence = self.env['ir.sequence'].sudo()
            val = {
                'name': _('POS Order %s', vals['name']),
                'padding': 4,
                'prefix': "%s/" % vals['name'],
                'code': "pos.order",
                'company_id': vals.get('company_id', False),
                'implementation': self._config_sequence_implementation(),
            }
            # force sequence_id field to new pos.order sequence
            vals['sequence_id'] = IrSequence.create(val).id

            val.update(name=_('POS order line %s', vals['name']), code='pos.order.line')
            vals['sequence_line_id'] = IrSequence.create(val).id
        pos_configs = super().create(vals_list)
        pos_configs.sudo()._check_modules_to_install()
        pos_configs.sudo()._check_groups_implied()
        pos_configs._update_preparation_printers_menuitem_visibility()
        # If you plan to add something after this, use a new environment. The one above is no longer valid after the modules install.
        return pos_configs

    def _reset_default_on_vals(self, vals):
        if 'tip_product_id' in vals and not vals['tip_product_id'] and 'iface_tipproduct' in vals and vals['iface_tipproduct']:
            default_product = self.env.ref('point_of_sale.product_product_tip', False)
            if default_product:
                vals['tip_product_id'] = default_product.id
            else:
                raise UserError(_('The default tip product is missing. Please manually specify the tip product. (See Tips field.)'))

    def _update_preparation_printers_menuitem_visibility(self):
        prepa_printers_menuitem = self.sudo().env.ref('point_of_sale.menu_pos_preparation_printer', raise_if_not_found=False)
        if prepa_printers_menuitem:
            prepa_printers_menuitem.active = self.sudo().env['pos.config'].search_count([('is_order_printer', '=', True)], limit=1) > 0

    def write(self, vals):
        self._check_header_footer(vals)
        self._reset_default_on_vals(vals)
        if ('is_order_printer' in vals and not vals['is_order_printer']):
            vals['printer_ids'] = [fields.Command.clear()]

        bypass_categories_forbidden_change = self.env.context.get('bypass_categories_forbidden_change', False)
        bypass_payment_method_ids_forbidden_change = self.env.context.get('bypass_payment_method_ids_forbidden_change', False)

        opened_session = self.mapped('session_ids').filtered(lambda s: s.state != 'closed')
        if opened_session:
            forbidden_fields = []
            for key in self._get_forbidden_change_fields():
                if key in vals.keys():
                    if bypass_categories_forbidden_change and key in ('limit_categories', 'iface_available_categ_ids'):
                        continue
                    if bypass_payment_method_ids_forbidden_change and key == 'payment_method_ids':
                        continue
                    if key == 'use_pricelist' and vals[key]:
                        continue
                    if key == 'available_pricelist_ids':
                        removed_pricelist = set(self.available_pricelist_ids.ids) - set(vals[key][0][2])
                        if len(removed_pricelist) == 0:
                            continue
                    field_name = self._fields[key].get_description(self.env)["string"]
                    forbidden_fields.append(field_name)
            if len(forbidden_fields) > 0:
                raise UserError(_(
                    "Unable to modify this PoS Configuration because you can't modify %s while a session is open.",
                    ", ".join(forbidden_fields)
                ))

        self._preprocess_x2many_vals_from_settings_view(vals)
        vals = self._keep_new_vals(vals)
        result = super(PosConfig, self).write(vals)

        self.sudo()._set_fiscal_position()
        self.sudo()._check_modules_to_install()
        self.sudo()._check_groups_implied()
        if 'is_order_printer' in vals:
            self._update_preparation_printers_menuitem_visibility()
        return result

    def _preprocess_x2many_vals_from_settings_view(self, vals):
        """ From the res.config.settings view, changes in the x2many fields always result to an array of link commands or a single set command.
            - As a result, the items that should be unlinked are not properly unlinked.
            - So before doing the write, we inspect the commands to determine which records should be unlinked.
            - We only care about the link command.
            - We can consider set command as absolute as it will replace all.
        """
        from_settings_view = self.env.context.get('from_settings_view')
        if not from_settings_view:
            # If vals is not from the settings view, we don't need to preprocess.
            return

        # Only ensure one when write is from settings view.
        self.ensure_one()

        fields_to_preprocess = []
        for f in self.fields_get([]).values():
            if f['type'] in ['many2many', 'one2many']:
                fields_to_preprocess.append(f['name'])

        for x2many_field in fields_to_preprocess:
            if x2many_field in vals:
                linked_ids = set(self[x2many_field].ids)

                for command in vals[x2many_field]:
                    if command[0] == 4:
                        _id = command[1]
                        if _id in linked_ids:
                            linked_ids.remove(_id)

                # Remaining items in linked_ids should be unlinked.
                unlink_commands = [Command.unlink(_id) for _id in linked_ids]

                vals[x2many_field] = unlink_commands + vals[x2many_field]

    def _keep_new_vals(self, vals):
        """ Keep values in vals that are different than
        self's values.
        """
        from_settings_view = self.env.context.get('from_settings_view')
        if not from_settings_view:
            return vals
        new_vals = {}
        for field, val in vals.items():
            config_field = self._fields.get(field)
            if config_field:
                cache_value = config_field.convert_to_cache(val, self)
                record_value = config_field.convert_to_record(cache_value, self)
                if record_value != self[field]:
                    new_vals[field] = val
        return new_vals

    def _get_forbidden_change_fields(self):
        forbidden_keys = ['module_pos_hr', 'module_pos_restaurant', 'available_pricelist_ids',
                          'limit_categories', 'iface_available_categ_ids', 'use_pricelist', 'module_pos_discount',
                          'payment_method_ids', 'iface_tipproduc']
        return forbidden_keys

    def unlink(self):
        # Delete the pos.config records first then delete the sequences linked to them
        sequences_to_delete = self.sequence_id | self.sequence_line_id
        res = super(PosConfig, self).unlink()
        sequences_to_delete.unlink()
        return res

    # TODO-JCB: Maybe we can move this logic in `_reset_default_on_vals`
    def _set_fiscal_position(self):
        for config in self:
            if config.tax_regime_selection and config.default_fiscal_position_id and (config.default_fiscal_position_id.id not in config.fiscal_position_ids.ids):
                config.fiscal_position_ids = [(4, config.default_fiscal_position_id.id)]
            elif not config.tax_regime_selection and config.fiscal_position_ids.ids:
                config.fiscal_position_ids = [(5, 0, 0)]

    def _check_modules_to_install(self):
        # determine modules to install
        expected = [
            fname[7:]           # 'module_account' -> 'account'
            for fname in self._fields
            if fname.startswith('module_')
            if any(pos_config[fname] for pos_config in self)
        ]
        if expected:
            STATES = ('installed', 'to install', 'to upgrade')
            modules = self.env['ir.module.module'].sudo().search([('name', 'in', expected)])
            modules = modules.filtered(lambda module: module.state not in STATES)
            if modules:
                modules.button_immediate_install()
                # just in case we want to do something if we install a module. (like a refresh ...)
                return True
        return False

    def _check_groups_implied(self):
        for pos_config in self:
            for field_name in [f for f in pos_config._fields if f.startswith('group_')]:
                field = pos_config._fields[field_name]
                if field.type in ('boolean', 'selection') and hasattr(field, 'implied_group'):
                    field_group_xmlids = getattr(field, 'group', 'base.group_user').split(',')
                    field_groups = self.env['res.groups'].concat(*(self.env.ref(it) for it in field_group_xmlids))
                    field_groups.write({'implied_ids': [(4, self.env.ref(field.implied_group).id)]})


    def execute(self):
        return {
             'type': 'ir.actions.client',
             'tag': 'reload',
         }

    def _force_http(self):
        enforce_https = self.env['ir.config_parameter'].sudo().get_param('point_of_sale.enforce_https')
        if not enforce_https and (self.other_devices or self.printer_ids.filtered(lambda pt: pt.printer_type == 'epson_epos')):
            return True
        return False

    # Methods to open the POS
    def _action_to_open_ui(self):
        if not self.current_session_id:
            self.env['pos.session'].create({'user_id': self.env.uid, 'config_id': self.id})
        path = '/pos/web' if self._force_http() else '/pos/ui'
        pos_url = path + '?config_id=%d' % self.id
        debug = request and request.session.debug
        if debug:
            pos_url += '&debug=%s' % debug
        return {
            'type': 'ir.actions.act_url',
            'url': pos_url,
            'target': 'self',
        }

    def _check_before_creating_new_session(self):
        self._check_company_has_template()
        self._check_pricelists()
        self._check_company_payment()
        self._check_currencies()
        self._check_profit_loss_cash_journal()
        self._check_payment_method_ids()

    def open_ui(self):
        """Open the pos interface with config_id as an extra argument.

        In vanilla PoS each user can only have one active session, therefore it was not needed to pass the config_id
        on opening a session. It is also possible to login to sessions created by other users.

        :returns: dict
        """
        self.ensure_one()
        if not self.current_session_id:
            self._check_before_creating_new_session()
        self._validate_fields(self._fields)

        return self._action_to_open_ui()

    def open_existing_session_cb(self):
        """ close session button

        access session form to validate entries
        """
        self.ensure_one()
        return self._open_session(self.current_session_id.id)

    def _open_session(self, session_id):
        self._check_pricelists()  # The pricelist company might have changed after the first opening of the session
        return {
            'name': _('Session'),
            'view_mode': 'form,tree',
            'res_model': 'pos.session',
            'res_id': session_id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    def open_opened_rescue_session_form(self):
        self.ensure_one()
        return {
            'res_model': 'pos.session',
            'view_mode': 'form',
            'res_id': self.session_ids.filtered(lambda s: s.state != 'closed' and s.rescue).id,
            'type': 'ir.actions.act_window',
        }

    # All following methods are made to create data needed in POS, when a localisation
    # is installed, or if POS is installed on database having companies that already have
    # a localisation installed
    @api.model
    def post_install_pos_localisation(self, companies=False):
        self = self.sudo()
        if not companies:
            companies = self.env['res.company'].search([])
        for company in companies.filtered('chart_template'):
            domain = AND([
                [('company_id', '=', company.id), ('module_pos_restaurant', '=', False)],
                OR([[('active', '=', True)], [('active', '=', False)]]),
            ])
            pos_configs = self.search(domain)
            if not pos_configs:
                self = self.with_company(company)
                pos_configs = self.env['pos.config'].create({
                'name': _('Shop'),
                'company_id': company.id,
                'module_pos_restaurant': False,
            })
            pos_configs.setup_defaults(company)

    def setup_defaults(self, company):
        """Extend this method to customize the existing pos.config of the company during the installation
        of a localisation.

        :param self pos.config: pos.config records present in the company during the installation of localisation.
        :param company res.company: the single company where the pos.config defaults will be setup.
        """
        self.assign_payment_journals(company)
        self.generate_pos_journal(company)
        self.setup_invoice_journal(company)

    def assign_payment_journals(self, company):
        for pos_config in self:
            if pos_config.payment_method_ids or pos_config.has_active_session:
                continue
            cash_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'cash'),
                ('currency_id', 'in', [pos_config.currency_id.id, False]),
            ], limit=1)
            bank_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'bank'),
                ('currency_id', 'in', [pos_config.currency_id.id, False]),
            ], limit=1)
            payment_methods = self.env['pos.payment.method']
            if cash_journal and len(cash_journal.pos_payment_method_ids.ids) == 0:
                payment_methods |= payment_methods.create({
                    'name': _('Cash'),
                    'journal_id': cash_journal.id,
                    'company_id': company.id,
                })
            if bank_journal:
                payment_methods |= payment_methods.create({
                    'name': _('Bank'),
                    'journal_id': bank_journal.id,
                    'company_id': company.id,
                })
            payment_methods |= payment_methods.create({
                'name': _('Customer Account'),
                'company_id': company.id,
                'split_transactions': True,
            })
            pos_config.write({'payment_method_ids': [(6, 0, payment_methods.ids)]})

    def generate_pos_journal(self, company):
        for pos_config in self:
            if pos_config.journal_id:
                continue
            pos_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('code', '=', 'POSS'),
            ])
            if not pos_journal:
                pos_journal = self.env['account.journal'].create({
                    'type': 'general',
                    'name': _('Point of Sale'),
                    'code': 'POSS',
                    'company_id': company.id,
                    'sequence': 20
                })
            pos_config.write({'journal_id': pos_journal.id})

    def setup_invoice_journal(self, company):
        for pos_config in self:
            invoice_journal_id = pos_config.invoice_journal_id or self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'sale'),
            ], limit=1)
            if invoice_journal_id:
                pos_config.write({'invoice_journal_id': invoice_journal_id.id})

    def _get_available_product_domain(self):
        domain = [
            *self.env['product.product']._check_company_domain(self.company_id),
            ('available_in_pos', '=', True),
            ('sale_ok', '=', True),
        ]
        if self.limit_categories and self.iface_available_categ_ids:
            domain.append(('pos_categ_ids', 'in', self.iface_available_categ_ids.ids))
        if self.iface_tipproduct:
            domain = OR([domain, [('id', '=', self.tip_product_id.id)]])
        return domain

    def _link_same_non_cash_payment_methods_if_exists(self, source_config_ref_id):
        src_cfg = self.env.ref(source_config_ref_id, raise_if_not_found=False)
        if src_cfg and src_cfg.company_id == self.company_id:
            self._link_same_non_cash_payment_methods(src_cfg)

    def _link_same_non_cash_payment_methods(self, source_config):
        pms = source_config.payment_method_ids.filtered(lambda pm: not pm.is_cash_count)
        if pms:
            self.payment_method_ids = [Command.link(pm.id) for pm in pms]

    def _is_journal_exist(self, journal_code, name, company_id):
        account_journal = self.env['account.journal']
        existing_journal = account_journal.search([
            ('name', '=', name),
            ('code', '=', journal_code),
            ('company_id', '=', company_id),
        ], limit=1)

        return existing_journal.id or account_journal.create({
            'name': name,
            'code': journal_code,
            'type': 'cash',
            'company_id': company_id,
        }).id

    def _is_pos_pm_exist(self, name, journal_id, company_id):
        pos_payment = self.env['pos.payment.method']
        existing_pos_cash_pm = pos_payment.search([
            ('name', '=', name),
            ('journal_id', '=', journal_id),
            ('company_id', '=', company_id),
        ], limit=1)

        return existing_pos_cash_pm.id or pos_payment.create({
            'name': name,
            'journal_id': journal_id,
            'company_id': company_id,
        }).id

    def _ensure_cash_payment_method(self, journal_code, name):
        self.ensure_one()
        if not self.company_id.chart_template or self.payment_method_ids.filtered('is_cash_count'):
            return
        company_id = self.company_id.id
        cash_journal_id = self._is_journal_exist(journal_code, name, company_id)
        cash_pm_id = self._is_pos_pm_exist(name, cash_journal_id, company_id)
        self.payment_method_ids = [Command.link(cash_pm_id)]

    def get_limited_products_loading(self, fields):
        tables, where_clause, params = self.env['product.product']._where_calc(
            self._get_available_product_domain()
        ).get_sql()
        query = f"""
            WITH pm AS (
                  SELECT product_id,
                         Max(write_date) date
                    FROM stock_move_line
                GROUP BY product_id
                ORDER BY date DESC
            )
               SELECT product_product.id
                 FROM {tables}
            LEFT JOIN pm ON product_product.id=pm.product_id
                WHERE {where_clause}
                ORDER BY product_product__product_tmpl_id.priority DESC,
                    case when product_product__product_tmpl_id.detailed_type = 'service' then 1 else 0 end DESC,
                    pm.date DESC NULLS LAST,
                    product_product.write_date
                LIMIT %s
        """
        self.env.cr.execute(query, params + [self.get_limited_product_count()])
        product_ids = self.env.cr.fetchall()
        products = self.env['product.product'].search([('id', 'in', product_ids)])
        product_combo = products.filtered(lambda p: p['detailed_type'] == 'combo')
        product_in_combo = product_combo.combo_ids.combo_line_ids.product_id
        products_available = products | product_in_combo
        return products_available.read(fields)

    def get_limited_product_count(self):
        default_limit = 20000
        config_param = self.env['ir.config_parameter'].sudo().get_param('point_of_sale.limited_product_count', default_limit)
        try:
            return int(config_param)
        except (TypeError, ValueError, OverflowError):
            return default_limit

    def toggle_images(self, for_products, for_categories):
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.show_product_images', for_products)
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.show_category_images', for_categories)

    def get_limited_partners_loading(self):
        self.env.cr.execute("""
            WITH pm AS
            (
                     SELECT   partner_id,
                              Count(partner_id) order_count
                     FROM     pos_order
                     GROUP BY partner_id)
            SELECT    id
            FROM      res_partner AS partner
            LEFT JOIN pm
            ON        (
                                partner.id = pm.partner_id)
            WHERE (
                partner.company_id=%s OR partner.company_id IS NULL
            )
            ORDER BY  COALESCE(pm.order_count, 0) DESC,
                      NAME limit %s;
        """, [self.company_id.id, str(100)])
        result = self.env.cr.fetchall()
        return result

    def action_pos_config_modal_edit(self):
        return {
            'view_mode': 'form',
            'res_model': 'pos.config',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
            'context': {'pos_config_open_modal': True},
        }

    def _add_trusted_config_id(self, config_id):
        self.trusted_config_ids += config_id

    def _remove_trusted_config_id(self, config_id):
        self.trusted_config_ids -= config_id

    @api.model
    def add_cash_payment_method(self):
        companies = self.env['res.company'].search([])
        for company in companies.filtered('chart_template'):
            pos_configs = self.search([
                *self._check_company_domain(company),
            ])
            journal_counter = 1
            for pos_config in pos_configs:
                if pos_config.payment_method_ids.filtered('is_cash_count'):
                    continue
                journal_counter += self.env['account.journal'].search_count([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'cash'),
                    ('pos_payment_method_ids', '=', False),
                ])
                cash_journal = self.env['account.journal'].create({
                    'name': _('Cash %s', journal_counter),
                    'code': 'RCSH%s' % journal_counter,
                    'type': 'cash',
                    'company_id': company.id
                })
                journal_counter += 1
                payment_methods = pos_config.payment_method_ids
                payment_methods |= self.env['pos.payment.method'].create({
                    'name': _('Cash %s', pos_config.name),
                    'journal_id': cash_journal.id,
                    'company_id': company.id,
                })
                pos_config.with_context(bypass_payment_method_ids_forbidden_change=True).write({'payment_method_ids': [(6, 0, payment_methods.ids)]})

    def _get_payment_method(self, payment_type):
        for pm in self.payment_method_ids:
            if pm.type == payment_type:
                return pm
        return False

    def _get_special_products(self):
        default_discount_product = self.env.ref('point_of_sale.product_product_consumable', raise_if_not_found=False) or self.env['product.product']
        default_tip_product = self.env.ref('point_of_sale.product_product_tip', raise_if_not_found=False) or self.env['product.product']
        return default_tip_product | default_discount_product
