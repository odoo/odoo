# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountCashboxLine(models.Model):
    _inherit = 'account.cashbox.line'

    default_pos_id = fields.Many2one('pos.config', string='This cashbox line is used by default when opening or closing a balance for this point of sale')

    @api.multi
    def name_get(self):
        result = []
        for cashbox_line in self:
            result.append((cashbox_line.id, "%s * %s"%(cashbox_line.coin_value, cashbox_line.number)))
        return result

class AccountBankStmtCashWizard(models.Model):
    _inherit = 'account.bank.statement.cashbox'

    @api.model
    def default_get(self, fields):
        vals = super(AccountBankStmtCashWizard, self).default_get(fields)
        config_id = self.env.context.get('default_pos_id')
        if config_id:
            lines = self.env['account.cashbox.line'].search([('default_pos_id', '=', config_id)])
            if self.env.context.get('balance', False) == 'start':
                vals['cashbox_lines_ids'] = [[0, 0, {'coin_value': line.coin_value, 'number': line.number, 'subtotal': line.subtotal}] for line in lines]
            else:
                vals['cashbox_lines_ids'] = [[0, 0, {'coin_value': line.coin_value, 'number': 0, 'subtotal': 0.0}] for line in lines]
        return vals

class PosConfig(models.Model):
    _name = 'pos.config'

    def _default_sale_journal(self):
        journal = self.env.ref('point_of_sale.pos_sale_journal', raise_if_not_found=False)
        if journal and journal.sudo().company_id == self.env.user.company_id:
            return journal
        return self._default_invoice_journal()

    def _default_invoice_journal(self):
        return self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.user.company_id.id)], limit=1)

    def _default_pricelist(self):
        return self.env['product.pricelist'].search([('currency_id', '=', self.env.user.company_id.currency_id.id)], limit=1)

    def _get_default_location(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id

    def _get_group_pos_manager(self):
        return self.env.ref('point_of_sale.group_pos_manager')

    def _get_group_pos_user(self):
        return self.env.ref('point_of_sale.group_pos_user')

    def _compute_default_customer_html(self):
        return self.env['ir.qweb'].render('point_of_sale.customer_facing_display_html')

    name = fields.Char(string='Point of Sale Name', index=True, required=True, help="An internal identification of the point of sale.")
    is_installed_account_accountant = fields.Boolean(compute="_compute_is_installed_account_accountant")
    journal_ids = fields.Many2many(
        'account.journal', 'pos_config_journal_rel',
        'pos_config_id', 'journal_id', string='Available Payment Methods',
        domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]",)
    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type')
    use_existing_lots = fields.Boolean(related='picking_type_id.use_existing_lots')
    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')], required=True, default=_get_default_location)
    journal_id = fields.Many2one(
        'account.journal', string='Sales Journal',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to post sales entries.",
        default=_default_sale_journal)
    invoice_journal_id = fields.Many2one(
        'account.journal', string='Invoice Journal',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to create invoices.",
        default=_default_invoice_journal)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', string="Currency")
    iface_cashdrawer = fields.Boolean(string='Cashdrawer', help="Automatically open the cashdrawer.")
    iface_payment_terminal = fields.Boolean(string='Payment Terminal', help="Enables Payment Terminal integration.")
    iface_electronic_scale = fields.Boolean(string='Electronic Scale', help="Enables Electronic Scale integration.")
    iface_vkeyboard = fields.Boolean(string='Virtual KeyBoard', help=u"Don’t turn this option on if you take orders on smartphones or tablets. \n Such devices already benefit from a native keyboard.")
    iface_customer_facing_display = fields.Boolean(string='Customer Facing Display', help="Show checkout to customers with a remotely-connected screen.")
    iface_print_via_proxy = fields.Boolean(string='Print via Proxy', help="Bypass browser printing and prints via the hardware proxy.")
    iface_scan_via_proxy = fields.Boolean(string='Scan via Proxy', help="Enable barcode scanning with a remotely connected barcode scanner.")
    iface_invoicing = fields.Boolean(string='Invoicing', help='Enables invoice generation from the Point of Sale.')
    iface_big_scrollbars = fields.Boolean('Large Scrollbars', help='For imprecise industrial touchscreens.')
    iface_print_auto = fields.Boolean(string='Automatic Receipt Printing', default=False,
        help='The receipt will automatically be printed at the end of each order.')
    iface_print_skip_screen = fields.Boolean(string='Skip Preview Screen', default=True,
        help='The receipt screen will be skipped if the receipt can be printed automatically.')
    iface_precompute_cash = fields.Boolean(string='Prefill Cash Payment',
        help='The payment input will behave similarily to bank payment input, and will be prefilled with the exact due amount.')
    iface_tax_included = fields.Selection([('subtotal', 'Tax-Excluded Prices'), ('total', 'Tax-Included Prices')], "Tax Display", default='subtotal', required=True)
    iface_start_categ_id = fields.Many2one('pos.category', string='Initial Category',
        help='The point of sale will display this product category by default. If no category is specified, all available products will be shown.')
    iface_display_categ_images = fields.Boolean(string='Display Category Pictures',
        help="The product categories will be displayed with pictures.")
    restrict_price_control = fields.Boolean(string='Restrict Price Modifications to Managers',
        help="Only users with Manager access rights for PoS app can modify the product prices on orders.")
    cash_control = fields.Boolean(string='Cash Control', help="Check the amount of the cashbox at opening and closing.")
    receipt_header = fields.Text(string='Receipt Header', help="A short text that will be inserted as a header in the printed receipt.")
    receipt_footer = fields.Text(string='Receipt Footer', help="A short text that will be inserted as a footer in the printed receipt.")
    proxy_ip = fields.Char(string='IP Address', size=45,
        help='The hostname or ip address of the hardware proxy, Will be autodetected if left empty.')
    active = fields.Boolean(default=True)
    uuid = fields.Char(readonly=True, default=lambda self: str(uuid.uuid4()),
        help='A globally unique identifier for this pos configuration, used to prevent conflicts in client-generated data.')
    sequence_id = fields.Many2one('ir.sequence', string='Order IDs Sequence', readonly=True,
        help="This sequence is automatically created by Odoo but you can change it "
        "to customize the reference numbers of your orders.", copy=False)
    sequence_line_id = fields.Many2one('ir.sequence', string='Order Line IDs Sequence', readonly=True,
        help="This sequence is automatically created by Odoo but you can change it "
        "to customize the reference numbers of your orders lines.", copy=False)
    session_ids = fields.One2many('pos.session', 'config_id', string='Sessions')
    current_session_id = fields.Many2one('pos.session', compute='_compute_current_session', string="Current Session")
    current_session_state = fields.Char(compute='_compute_current_session')
    last_session_closing_cash = fields.Float(compute='_compute_last_session')
    last_session_closing_date = fields.Date(compute='_compute_last_session')
    pos_session_username = fields.Char(compute='_compute_current_session_user')
    pos_session_state = fields.Char(compute='_compute_current_session_user')
    group_by = fields.Boolean(string='Group Journal Items', default=True,
        help="Check this if you want to group the Journal Items by Product while closing a Session.")
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist', required=True, default=_default_pricelist,
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured.")
    available_pricelist_ids = fields.Many2many('product.pricelist', string='Available Pricelists', default=_default_pricelist,
        help="Make several pricelists available in the Point of Sale. You can also apply a pricelist to specific customers from their contact form (in Sales tab). To be valid, this pricelist must be listed here as an available pricelist. Otherwise the default pricelist will apply.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', string='Barcode Nomenclature',
        help='Defines what kind of barcodes are available and how they are assigned to products, customers and cashiers.')
    group_pos_manager_id = fields.Many2one('res.groups', string='Point of Sale Manager Group', default=_get_group_pos_manager,
        help='This field is there to pass the id of the pos manager group to the point of sale client.')
    group_pos_user_id = fields.Many2one('res.groups', string='Point of Sale User Group', default=_get_group_pos_user,
        help='This field is there to pass the id of the pos user group to the point of sale client.')
    iface_tipproduct = fields.Boolean(string="Product tips")
    tip_product_id = fields.Many2one('product.product', string='Tip Product',
        help="This product is used as reference on customer receipts.")
    fiscal_position_ids = fields.Many2many('account.fiscal.position', string='Fiscal Positions', help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.')
    default_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position')
    default_cashbox_lines_ids = fields.One2many('account.cashbox.line', 'default_pos_id', string='Default Balance')
    customer_facing_display_html = fields.Html(string='Customer facing display content', translate=True, default=_compute_default_customer_html)
    use_pricelist = fields.Boolean("Use a pricelist.")
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
                                          implied_group='product.group_sale_pricelist',
                                          help="""Allows to manage different prices based on rules per category of customers.
                    Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
                                          implied_group='product.group_pricelist_item')
    tax_regime = fields.Boolean("Tax Regime")
    tax_regime_selection = fields.Boolean("Tax Regime Selection value")
    barcode_scanner = fields.Boolean("Barcode Scanner")
    start_category = fields.Boolean("Set Start Category")
    module_pos_restaurant = fields.Boolean("Is a Bar/Restaurant")
    module_pos_discount = fields.Boolean("Global Discounts")
    module_pos_loyalty = fields.Boolean("Loyalty Program")
    module_pos_mercury = fields.Boolean(string="Integrated Card Payments")
    module_pos_reprint = fields.Boolean(string="Reprint Receipt")
    is_posbox = fields.Boolean("PosBox")
    is_header_or_footer = fields.Boolean("Header & Footer")

    def _compute_is_installed_account_accountant(self):
        account_accountant = self.env['ir.module.module'].sudo().search([('name', '=', 'account_accountant'), ('state', '=', 'installed')])
        for pos_config in self:
            pos_config.is_installed_account_accountant = account_accountant and account_accountant.id

    @api.depends('journal_id.currency_id', 'journal_id.company_id.currency_id')
    def _compute_currency(self):
        for pos_config in self:
            if pos_config.journal_id:
                pos_config.currency_id = pos_config.journal_id.currency_id.id or pos_config.journal_id.company_id.currency_id.id
            else:
                pos_config.currency_id = self.env.user.company_id.currency_id.id

    @api.depends('session_ids')
    def _compute_current_session(self):
        for pos_config in self:
            session = pos_config.session_ids.filtered(lambda r: r.user_id.id == self.env.uid and \
                not r.state == 'closed' and \
                not r.rescue)
            # sessions ordered by id desc
            pos_config.current_session_id = session and session[0].id or False
            pos_config.current_session_state = session and session[0].state or False

    @api.depends('session_ids')
    def _compute_last_session(self):
        PosSession = self.env['pos.session']
        for pos_config in self:
            session = PosSession.search_read(
                [('config_id', '=', pos_config.id), ('state', '=', 'closed')],
                ['cash_register_balance_end_real', 'stop_at'],
                order="stop_at desc", limit=1)
            if session:
                pos_config.last_session_closing_cash = session[0]['cash_register_balance_end_real']
                pos_config.last_session_closing_date = session[0]['stop_at']
            else:
                pos_config.last_session_closing_cash = 0
                pos_config.last_session_closing_date = False

    @api.depends('session_ids')
    def _compute_current_session_user(self):
        for pos_config in self:
            session = pos_config.session_ids.filtered(lambda s: s.state in ['opening_control', 'opened', 'closing_control'] and not s.rescue)
            pos_config.pos_session_username = session and session[0].user_id.name or False
            pos_config.pos_session_state = session and session[0].state or False

    @api.constrains('company_id', 'stock_location_id')
    def _check_company_location(self):
        if self.stock_location_id.company_id and self.stock_location_id.company_id.id != self.company_id.id:
            raise ValidationError(_("The company of the stock location is different than the one of point of sale"))

    @api.constrains('company_id', 'journal_id')
    def _check_company_journal(self):
        if self.journal_id and self.journal_id.company_id.id != self.company_id.id:
            raise ValidationError(_("The company of the sales journal is different than the one of point of sale"))

    @api.constrains('company_id', 'invoice_journal_id')
    def _check_company_invoice_journal(self):
        if self.invoice_journal_id and self.invoice_journal_id.company_id.id != self.company_id.id:
            raise ValidationError(_("The invoice journal and the point of sale must belong to the same company"))

    @api.constrains('company_id', 'journal_ids')
    def _check_company_payment(self):
        if self.env['account.journal'].search_count([('id', 'in', self.journal_ids.ids), ('company_id', '!=', self.company_id.id)]):
            raise ValidationError(_("The company of a payment method is different than the one of point of sale"))

    @api.constrains('pricelist_id', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id', 'journal_ids')
    def _check_currencies(self):
        if self.pricelist_id not in self.available_pricelist_ids:
            raise ValidationError(_("The default pricelist must be included in the available pricelists."))
        if any(self.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != self.currency_id)):
            raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                    " as the Sales Journal set on this point of sale if you use"
                                    " the Accounting application."))
        if self.invoice_journal_id.currency_id and self.invoice_journal_id.currency_id != self.currency_id:
            raise ValidationError(_("The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))
        if any(self.journal_ids.mapped(lambda journal: journal.currency_id and journal.currency_id != self.currency_id)):
            raise ValidationError(_("All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))

    @api.onchange('iface_print_via_proxy')
    def _onchange_iface_print_via_proxy(self):
        self.iface_print_auto = self.iface_print_via_proxy

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        if self.picking_type_id.default_location_src_id.usage == 'internal' and self.picking_type_id.default_location_dest_id.usage == 'customer':
            self.stock_location_id = self.picking_type_id.default_location_src_id.id

    @api.onchange('use_pricelist')
    def _onchange_use_pricelist(self):
        """
        If the 'pricelist' box is unchecked, we reset the pricelist_id to stop
        using a pricelist for this posbox. 
        """
        if not self.use_pricelist:
            self.pricelist_id = self._default_pricelist()
        else:
            self.update({
                'group_sale_pricelist': True,
                'group_pricelist_item': True,
            })

    @api.onchange('available_pricelist_ids')
    def _onchange_available_pricelist_ids(self):
        if self.pricelist_id not in self.available_pricelist_ids:
            self.pricelist_id = False

    @api.onchange('iface_scan_via_proxy')
    def _onchange_iface_scan_via_proxy(self):
        if self.iface_scan_via_proxy:
            self.barcode_scanner = True
        else:
            self.barcode_scanner = False

    @api.onchange('barcode_scanner')
    def _onchange_barcode_scanner(self):
        if self.barcode_scanner:
            self.barcode_nomenclature_id = self.env['barcode.nomenclature'].search([], limit=1)
        else:
            self.barcode_nomenclature_id = False

    @api.onchange('is_posbox')
    def _onchange_is_posbox(self):
        if not self.is_posbox:
            self.proxy_ip = False
            self.iface_scan_via_proxy = False
            self.iface_electronic_scale = False
            self.iface_cashdrawer = False
            self.iface_print_via_proxy = False
            self.iface_customer_facing_display = False

    @api.onchange('tax_regime')
    def _onchange_tax_regime(self):
        if not self.tax_regime:
            self.default_fiscal_position_id = False

    @api.onchange('tax_regime_selection')
    def _onchange_tax_regime_selection(self):
        if not self.tax_regime_selection:
            self.fiscal_position_ids = [(5, 0, 0)]

    @api.onchange('start_category')
    def _onchange_start_category(self):
        if not self.start_category:
            self.iface_start_categ_id = False

    @api.onchange('is_header_or_footer')
    def _onchange_header_footer(self):
        if not self.is_header_or_footer:
            self.receipt_header = False
            self.receipt_footer = False

    @api.multi
    def name_get(self):
        result = []
        for config in self:
            if (not config.session_ids) or (config.session_ids[0].state == 'closed'):
                result.append((config.id, config.name + ' (' + _('not used') + ')'))
                continue
            result.append((config.id, config.name + ' (' + config.session_ids[0].user_id.name + ')'))
        return result

    @api.model
    def create(self, values):
        if values.get('is_posbox') and values.get('iface_customer_facing_display'):
            if values.get('customer_facing_display_html') and not values['customer_facing_display_html'].strip():
                values['customer_facing_display_html'] = self._compute_default_customer_html()
        IrSequence = self.env['ir.sequence'].sudo()
        val = {
            'name': _('POS Order %s') % values['name'],
            'padding': 4,
            'prefix': "%s/" % values['name'],
            'code': "pos.order",
            'company_id': values.get('company_id', False),
        }
        # force sequence_id field to new pos.order sequence
        values['sequence_id'] = IrSequence.create(val).id

        val.update(name=_('POS order line %s') % values['name'], code='pos.order.line')
        values['sequence_line_id'] = IrSequence.create(val).id
        pos_config = super(PosConfig, self).create(values)
        pos_config.sudo()._check_modules_to_install()
        pos_config.sudo()._check_groups_implied()
        # If you plan to add something after this, use a new environment. The one above is no longer valid after the modules install.
        return pos_config

    @api.multi
    def write(self, vals):
        if (self.is_posbox or vals.get('is_posbox')) and (self.iface_customer_facing_display or vals.get('iface_customer_facing_display')):
            facing_display = (self.customer_facing_display_html or vals.get('customer_facing_display_html') or '').strip()
            if not facing_display:
                vals['customer_facing_display_html'] = self._compute_default_customer_html()
        result = super(PosConfig, self).write(vals)
        self.sudo()._set_fiscal_position()
        self.sudo()._check_modules_to_install()
        self.sudo()._check_groups_implied()
        return result

    @api.multi
    def unlink(self):
        for pos_config in self.filtered(lambda pos_config: pos_config.sequence_id or pos_config.sequence_line_id):
            pos_config.sequence_id.unlink()
            pos_config.sequence_line_id.unlink()
        return super(PosConfig, self).unlink()

    def _set_fiscal_position(self):
        for config in self:
            if config.tax_regime and config.default_fiscal_position_id.id not in config.fiscal_position_ids.ids:
                config.fiscal_position_ids = [(4, config.default_fiscal_position_id.id)]
            elif not config.tax_regime_selection and not config.tax_regime and config.fiscal_position_ids.ids:
                config.fiscal_position_ids = [(5, 0, 0)]

    def _check_modules_to_install(self):
        module_installed = False
        for pos_config in self:
            for field_name in [f for f in pos_config.fields_get_keys() if f.startswith('module_')]:
                module_name = field_name.split('module_')[1]
                module_to_install = self.env['ir.module.module'].sudo().search([('name', '=', module_name)])
                if getattr(pos_config, field_name) and module_to_install.state not in ('installed', 'to install', 'to upgrade'):
                    module_to_install.button_immediate_install()
                    module_installed = True
        # just in case we want to do something if we install a module. (like a refresh ...)
        return module_installed

    def _check_groups_implied(self):
        for pos_config in self:
            for field_name in [f for f in pos_config.fields_get_keys() if f.startswith('group_')]:
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

    # Methods to open the POS
    @api.multi
    def open_ui(self):
        """ open the pos interface """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url':   '/pos/web/',
            'target': 'self',
        }

    @api.multi
    def open_session_cb(self):
        """ new session button

        create one if none exist
        access cash control interface if enabled or start a session
        """
        self.ensure_one()
        if not self.current_session_id:
            self.current_session_id = self.env['pos.session'].create({
                'user_id': self.env.uid,
                'config_id': self.id
            })
            if self.current_session_id.state == 'opened':
                return self.open_ui()
            return self._open_session(self.current_session_id.id)
        return self._open_session(self.current_session_id.id)

    @api.multi
    def open_existing_session_cb(self):
        """ close session button

        access session form to validate entries
        """
        self.ensure_one()
        return self._open_session(self.current_session_id.id)

    def _open_session(self, session_id):
        return {
            'name': _('Session'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'pos.session',
            'res_id': session_id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
