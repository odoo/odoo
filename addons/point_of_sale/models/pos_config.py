# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from uuid import uuid4
import pytz

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError


class PosConfig(models.Model):
    _name = 'pos.config'
    _description = 'Point of Sale Configuration'

    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).id

    def _default_picking_type_id(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).pos_type_id.id

    def _default_sale_journal(self):
        return self.env['account.journal'].search([('type', 'in', ('sale', 'general')), ('company_id', '=', self.env.company.id), ('code', '=', 'POSS')], limit=1)

    def _default_invoice_journal(self):
        return self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1)

    def _default_payment_methods(self):
        """ Should only default to payment methods that are compatible to this config's company and currency.
        """
        return self.env['pos.payment.method'].search([
            ('split_transactions', '=', False),
            ('company_id', '=', self.env.company.id),
            '|',
                ('journal_id', '=', False),
                ('journal_id.currency_id', 'in', (False, self.env.company.currency_id.id)),
        ])

    def _default_pricelist(self):
        return self.env['product.pricelist'].search([('company_id', 'in', (False, self.env.company.id)), ('currency_id', '=', self.env.company.currency_id.id)], limit=1)

    def _get_group_pos_manager(self):
        return self.env.ref('point_of_sale.group_pos_manager')

    def _get_group_pos_user(self):
        return self.env.ref('point_of_sale.group_pos_user')

    name = fields.Char(string='Point of Sale', required=True, help="An internal identification of the point of sale.")
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
        help="Accounting journal used to post POS session journal entries and POS invoice payments.",
        default=_default_sale_journal,
        ondelete='restrict')
    invoice_journal_id = fields.Many2one(
        'account.journal', string='Invoice Journal',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to create invoices.",
        default=_default_invoice_journal)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', string="Currency")
    iface_cashdrawer = fields.Boolean(string='Cashdrawer', help="Automatically open the cashdrawer.")
    iface_electronic_scale = fields.Boolean(string='Electronic Scale', help="Enables Electronic Scale integration.")
    iface_customer_facing_display = fields.Boolean(compute='_compute_customer_facing_display')
    iface_customer_facing_display_via_proxy = fields.Boolean(string='Customer Facing Display', help="Show checkout to customers with a remotely-connected screen.")
    iface_customer_facing_display_local = fields.Boolean(string='Local Customer Facing Display', help="Show checkout to customers.")
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
    number_of_opened_session = fields.Integer(string="Number of Opened Session", compute='_compute_current_session')
    last_session_closing_cash = fields.Float(compute='_compute_last_session')
    last_session_closing_date = fields.Date(compute='_compute_last_session')
    pos_session_username = fields.Char(compute='_compute_current_session_user')
    pos_session_state = fields.Char(compute='_compute_current_session_user')
    pos_session_duration = fields.Char(compute='_compute_current_session_user')
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist', required=True, default=_default_pricelist,
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured.")
    available_pricelist_ids = fields.Many2many('product.pricelist', string='Available Pricelists', default=_default_pricelist,
        help="Make several pricelists available in the Point of Sale. You can also apply a pricelist to specific customers from their contact form (in Sales tab). To be valid, this pricelist must be listed here as an available pricelist. Otherwise the default pricelist will apply.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', string='Barcode Nomenclature',
        help='Defines what kind of barcodes are available and how they are assigned to products, customers and cashiers.',
        default=lambda self: self.env.company.nomenclature_id, required=True)
    group_pos_manager_id = fields.Many2one('res.groups', string='Point of Sale Manager Group', default=_get_group_pos_manager,
        help='This field is there to pass the id of the pos manager group to the point of sale client.')
    group_pos_user_id = fields.Many2one('res.groups', string='Point of Sale User Group', default=_get_group_pos_user,
        help='This field is there to pass the id of the pos user group to the point of sale client.')
    iface_tipproduct = fields.Boolean(string="Product tips")
    tip_product_id = fields.Many2one('product.product', string='Tip Product',
        help="This product is used as reference on customer receipts.")
    fiscal_position_ids = fields.Many2many('account.fiscal.position', string='Fiscal Positions', help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.')
    default_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position')
    default_bill_ids = fields.Many2many('pos.bill', string="Coins/Bills")
    use_pricelist = fields.Boolean("Use a pricelist.")
    tax_regime_selection = fields.Boolean("Tax Regime Selection value")
    start_category = fields.Boolean("Start Category", default=False)
    limit_categories = fields.Boolean("Restrict Categories")
    module_pos_restaurant = fields.Boolean("Is a Bar/Restaurant")
    module_pos_discount = fields.Boolean("Global Discounts")
    module_pos_loyalty = fields.Boolean("Loyalty Program")
    module_pos_mercury = fields.Boolean(string="Integrated Card Payments")
    is_posbox = fields.Boolean("PosBox")
    is_header_or_footer = fields.Boolean("Custom Header & Footer")
    module_pos_hr = fields.Boolean(help="Show employee login screen")
    amount_authorized_diff = fields.Float('Amount Authorized Difference',
        help="This field depicts the maximum difference allowed between the ending balance and the theoretical cash when "
             "closing a session, for non-POS managers. If this maximum is reached, the user will have an error message at "
             "the closing of his session saying that he needs to contact his manager.")
    payment_method_ids = fields.Many2many('pos.payment.method', string='Payment Methods', default=lambda self: self._default_payment_methods())
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
    limited_products_loading = fields.Boolean('Limited Product Loading',
                                              default=True,
                                              help="we load all starred products (favorite), all services, recent inventory movements of products, and the most recently updated products.\n"
                                                   "When the session is open, we keep on loading all remaining products in the background.\n"
                                                   "In the meantime, you can click on the 'database icon' in the searchbar to load products from database.")
    limited_products_amount = fields.Integer(default=20000)
    product_load_background = fields.Boolean(default=True)
    limited_partners_loading = fields.Boolean('Limited Partners Loading',
                                              default=True,
                                              help="By default, 100 partners are loaded.\n"
                                                   "When the session is open, we keep on loading all remaining partners in the background.\n"
                                                   "In the meantime, you can use the 'Load Customers' button to load partners from database.")
    limited_partners_amount = fields.Integer(default=100)
    partner_load_background = fields.Boolean(default=True)

    @api.depends('payment_method_ids')
    def _compute_cash_control(self):
        for config in self:
            config.cash_control = bool(config.payment_method_ids.filtered('is_cash_count'))

    @api.depends('company_id')
    def _compute_company_has_template(self):
        for config in self:
            if config.company_id.chart_template_id:
                config.company_has_template = True
            else:
                config.company_has_template = False

    def _compute_is_installed_account_accountant(self):
        account_accountant = self.env['ir.module.module'].sudo().search([('name', '=', 'account_accountant'), ('state', '=', 'installed')])
        for pos_config in self:
            pos_config.is_installed_account_accountant = account_accountant and account_accountant.id

    @api.depends('journal_id.currency_id', 'journal_id.company_id.currency_id', 'company_id', 'company_id.currency_id')
    def _compute_currency(self):
        for pos_config in self:
            if pos_config.journal_id:
                pos_config.currency_id = pos_config.journal_id.currency_id.id or pos_config.journal_id.company_id.currency_id.id
            else:
                pos_config.currency_id = pos_config.company_id.currency_id.id

    @api.depends('session_ids', 'session_ids.state')
    def _compute_current_session(self):
        """If there is an open session, store it to current_session_id / current_session_State.
        """
        for pos_config in self:
            opened_sessions = pos_config.session_ids.filtered(lambda s: not s.state == 'closed')
            session = pos_config.session_ids.filtered(lambda s: not s.state == 'closed' and not s.rescue)
            # sessions ordered by id desc
            pos_config.number_of_opened_session = len(opened_sessions)
            pos_config.has_active_session = opened_sessions and True or False
            pos_config.current_session_id = session and session[0].id or False
            pos_config.current_session_state = session and session[0].state or False

    @api.depends('session_ids')
    def _compute_last_session(self):
        PosSession = self.env['pos.session']
        for pos_config in self:
            session = PosSession.search_read(
                [('config_id', '=', pos_config.id), ('state', '=', 'closed')],
                ['cash_register_balance_end_real', 'stop_at', 'cash_register_id'],
                order="stop_at desc", limit=1)
            if session:
                timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
                pos_config.last_session_closing_date = session[0]['stop_at'].astimezone(timezone).date()
                if session[0]['cash_register_id']:
                    pos_config.last_session_closing_cash = session[0]['cash_register_balance_end_real']
                else:
                    pos_config.last_session_closing_cash = 0
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

    @api.constrains('company_id', 'journal_id')
    def _check_company_journal(self):
        for config in self:
            if config.journal_id and config.journal_id.company_id.id != config.company_id.id:
                raise ValidationError(_("The sales journal of the point of sale %s must belong to its company.", config.name))

    def _check_profit_loss_cash_journal(self):
        if self.cash_control and self.payment_method_ids:
            for method in self.payment_method_ids:
                if method.is_cash_count and (not method.journal_id.loss_account_id or not method.journal_id.profit_account_id):
                    raise ValidationError(_("You need a loss and profit account on your cash journal."))

    @api.constrains('company_id', 'invoice_journal_id')
    def _check_company_invoice_journal(self):
        for config in self:
            if config.invoice_journal_id and config.invoice_journal_id.company_id.id != config.company_id.id:
                raise ValidationError(_("The invoice journal of the point of sale %s must belong to the same company.", config.name))

    @api.constrains('company_id', 'payment_method_ids')
    def _check_company_payment(self):
        for config in self:
            if self.env['pos.payment.method'].search_count([('id', 'in', config.payment_method_ids.ids), ('company_id', '!=', config.company_id.id)]):
                raise ValidationError(_("The payment methods for the point of sale %s must belong to its company.", self.name))

    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id', 'payment_method_ids')
    def _check_currencies(self):
        for config in self:
            if config.use_pricelist and config.pricelist_id not in config.available_pricelist_ids:
                raise ValidationError(_("The default pricelist must be included in the available pricelists."))

            # Check if the config's payment methods are compatible with its currency
            for pm in config.payment_method_ids:
                if pm.journal_id and pm.journal_id.currency_id and pm.journal_id.currency_id != config.currency_id:
                    raise ValidationError(_("All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))

        if any(self.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != self.currency_id)):
            raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                    " as the Sales Journal set on this point of sale if you use"
                                    " the Accounting application."))
        if self.invoice_journal_id.currency_id and self.invoice_journal_id.currency_id != self.currency_id:
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

    def name_get(self):
        result = []
        for config in self:
            last_session = self.env['pos.session'].search([('config_id', '=', config.id)], limit=1)
            if (not last_session) or (last_session.state == 'closed'):
                result.append((config.id, _("%(pos_name)s (not used)", pos_name=config.name)))
            else:
                result.append((config.id, "%s (%s)" % (config.name, last_session.user_id.name)))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            IrSequence = self.env['ir.sequence'].sudo()
            val = {
                'name': _('POS Order %s', vals['name']),
                'padding': 4,
                'prefix': "%s/" % vals['name'],
                'code': "pos.order",
                'company_id': vals.get('company_id', False),
            }
            # force sequence_id field to new pos.order sequence
            vals['sequence_id'] = IrSequence.create(val).id

            val.update(name=_('POS order line %s', vals['name']), code='pos.order.line')
            vals['sequence_line_id'] = IrSequence.create(val).id
        pos_configs = super().create(vals_list)
        pos_configs.sudo()._check_modules_to_install()
        pos_configs.sudo()._check_groups_implied()
        # If you plan to add something after this, use a new environment. The one above is no longer valid after the modules install.
        return pos_configs

    def _reset_default_on_vals(self, vals):
        if 'tip_product_id' in vals and any(self.mapped('iface_tipproduct')) and not vals['tip_product_id']:
            default_product = self.env.ref('point_of_sale.product_product_tip', False)
            if default_product:
                vals['tip_product_id'] = default_product.id
            else:
                raise UserError(_('The default tip product is missing. Please manually specify the tip product. (See Tips field.)'))

    def write(self, vals):
        self._reset_default_on_vals(vals)
        opened_session = self.mapped('session_ids').filtered(lambda s: s.state != 'closed')
        if opened_session:
            forbidden_fields = []
            for key in self._get_forbidden_change_fields():
                if key in vals.keys():
                    field_name = self._fields[key].get_description(self.env)["string"]
                    forbidden_fields.append(field_name)
            if len(forbidden_fields) > 0:
                raise UserError(_(
                    "Unable to modify this PoS Configuration because you can't modify %s while a session is open.",
                    ", ".join(forbidden_fields)
                ))
        result = super(PosConfig, self).write(vals)

        self.sudo()._set_fiscal_position()
        self.sudo()._check_modules_to_install()
        self.sudo()._check_groups_implied()
        return result

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
             'params': {'wait': True}
         }

    def _force_http(self):
        enforce_https = self.env['ir.config_parameter'].sudo().get_param('point_of_sale.enforce_https')
        if not enforce_https and self.other_devices:
            return True
        return False

    def _get_pos_base_url(self):
        return '/pos/web' if self._force_http() else '/pos/ui'

    # Methods to open the POS
    def open_ui(self):
        """Open the pos interface with config_id as an extra argument.

        In vanilla PoS each user can only have one active session, therefore it was not needed to pass the config_id
        on opening a session. It is also possible to login to sessions created by other users.

        :returns: dict
        """
        self.ensure_one()
        # check all constraints, raises if any is not met
        self._validate_fields(self._fields)
        return {
            'type': 'ir.actions.act_url',
            'url': self._get_pos_base_url() + '?config_id=%d' % self.id,
            'target': 'self',
        }

    def open_session_cb(self):
        """ new session button

        create one if none exist
        access cash control interface if enabled or start a session
        """
        self.ensure_one()
        if not self.current_session_id:
            self._check_pricelists()
            self._check_company_journal()
            self._check_company_invoice_journal()
            self._check_company_payment()
            self._check_currencies()
            self._check_profit_loss_cash_journal()
            self._check_payment_method_ids()
            self.env['pos.session'].create({
                'user_id': self.env.uid,
                'config_id': self.id
            })
        return self.open_ui()

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

    def open_opened_session_list(self):
        return {
            'name': _('Opened Sessions'),
            'res_model': 'pos.session',
            'view_mode': 'tree,kanban,form',
            'type': 'ir.actions.act_window',
            'domain': [('state', '!=', 'closed'), ('config_id', '=', self.id)]
        }

    # All following methods are made to create data needed in POS, when a localisation
    # is installed, or if POS is installed on database having companies that already have
    # a localisation installed
    @api.model
    def post_install_pos_localisation(self, companies=False):
        self = self.sudo()
        if not companies:
            companies = self.env['res.company'].search([])
        for company in companies.filtered('chart_template_id'):
            pos_configs = self.search([('company_id', '=', company.id)])
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
            cash_journal = self.env['account.journal'].search([('company_id', '=', company.id), ('type', '=', 'cash')], limit=1)
            bank_journal = self.env['account.journal'].search([('company_id', '=', company.id), ('type', '=', 'bank')], limit=1)
            payment_methods = self.env['pos.payment.method']
            if cash_journal:
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
            pos_journal = self.env['account.journal'].search([('company_id', '=', company.id), ('code', '=', 'POSS')])
            if not pos_journal:
                pos_journal = self.env['account.journal'].create({
                    'type': 'general',
                    'name': 'Point of Sale',
                    'code': 'POSS',
                    'company_id': company.id,
                    'sequence': 20
                })
            pos_config.write({'journal_id': pos_journal.id})

    def setup_invoice_journal(self, company):
        for pos_config in self:
            invoice_journal_id = pos_config.invoice_journal_id or self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
            if invoice_journal_id:
                pos_config.write({'invoice_journal_id': invoice_journal_id.id})

    def get_limited_products_loading(self, fields):
        query = """
            WITH pm AS (
                  SELECT product_id,
                         Max(write_date) date
                    FROM stock_quant
                GROUP BY product_id
            )
               SELECT p.id
                 FROM product_product p
            LEFT JOIN product_template t ON product_tmpl_id=t.id
            LEFT JOIN pm ON p.id=pm.product_id
                WHERE (
                        t.available_in_pos
                    AND t.sale_ok
                    AND (t.company_id=%(company_id)s OR t.company_id IS NULL)
                    AND %(available_categ_ids)s IS NULL OR t.pos_categ_id=ANY(%(available_categ_ids)s)
                )    OR p.id=%(tip_product_id)s
             ORDER BY t.priority DESC,
                      t.detailed_type DESC,
                      COALESCE(pm.date,p.write_date) DESC 
                LIMIT %(limit)s
        """
        params = {
            'company_id': self.company_id.id,
            'available_categ_ids': self.iface_available_categ_ids.mapped('id') if self.iface_available_categ_ids else None,
            'tip_product_id': self.tip_product_id.id if self.tip_product_id else None,
            'limit': self.limited_products_amount
        }
        self.env.cr.execute(query, params)
        product_ids = self.env.cr.fetchall()
        products = self.env['product.product'].search_read([('id', 'in', product_ids)], fields=fields)
        return products

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
        """, [self.company_id.id, str(self.limited_partners_amount)])
        result = self.env.cr.fetchall()
        return result

    @api.model
    def are_there_uninstalled_modules(self, changed_fields):
        modules_to_check = self._get_modules_to_check(changed_fields)
        n_installed = self.env['ir.module.module'].search_count([('name', 'in', modules_to_check), ('state', '=', 'installed')])
        return n_installed != len(modules_to_check)

    @api.model
    def _get_modules_to_check(self, changed_fields):
        modules_to_check = []
        for field in changed_fields:
            if field.startswith('module_'):
                modules_to_check.append(field.replace('module_', ''))
        return modules_to_check

    def action_pos_config_modal_edit(self):
        return {
            'view_mode': 'form',
            'res_model': 'pos.config',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
            'context': {'pos_config_open_modal': True},
        }
