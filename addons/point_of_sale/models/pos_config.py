# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from openerp import models, fields, api, _
from openerp.exceptions import UserError


class PosConfig(models.Model):
    _name = 'pos.config'

    POS_CONFIG_STATE = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated')
    ]

    def _default_sale_journal(self):
        return self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.user.company_id.id)], limit=1)

    def _default_pricelist(self):
        return self.env['product.pricelist'].search([], limit=1).id

    def _get_default_location(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id.id

    def _get_default_company(self):
        return self.env['res.users']._get_company()

    def _get_default_nomenclature(self):
        return self.env['barcode.nomenclature'].search([], limit=1)

    def _get_group_pos_manager(self):
        return self.env.ref('point_of_sale.group_pos_manager')

    def _get_group_pos_user(self):
        return self.env.ref('point_of_sale.group_pos_user')

    name = fields.Char(string='Point of Sale Name', index=True, required=True, help="An internal identification of the point of sale")
    journal_ids = fields.Many2many(
        'account.journal', 'pos_config_journal_rel',
        'pos_config_id', 'journal_id', string='Available Payment Methods',
        domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]",)
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')
    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')], required=True, default=_get_default_location)
    journal_id = fields.Many2one(
        'account.journal', string='Sale Journal',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to post sales entries.",
        default=_default_sale_journal)
    currency_id = fields.Many2one('res.currency', compute='_get_currency', string="Currency")
    iface_cashdrawer = fields.Boolean(string='Cashdrawer', help="Automatically open the cashdrawer")
    iface_payment_terminal = fields.Boolean(string='Payment Terminal', help="Enables Payment Terminal integration")
    iface_electronic_scale = fields.Boolean(string='Electronic Scale', help="Enables Electronic Scale integration")
    iface_vkeyboard = fields.Boolean(string='Virtual KeyBoard', help="Enables an integrated Virtual Keyboard")
    iface_print_via_proxy = fields.Boolean(string='Print via Proxy', help="Bypass browser printing and prints via the hardware proxy")
    iface_scan_via_proxy = fields.Boolean(string='Scan via Proxy', help="Enable barcode scanning with a remotely connected barcode scanner")
    iface_invoicing = fields.Boolean(string='Invoicing', help='Enables invoice generation from the Point of Sale', default=True)
    iface_big_scrollbars = fields.Boolean(string='Large Scrollbars', help='For imprecise industrial touchscreens')
    iface_fullscreen = fields.Boolean(string='Fullscreen', help='Display the Point of Sale in full screen mode')
    iface_print_auto = fields.Boolean(string='Automatic Receipt Printing', help='The receipt will automatically be p-rinted at the end of each order', default=True)
    iface_print_skip_screen = fields.Boolean(string='Skip Receipt Screen', help='The receipt screen will be skipped if the receipt can be printed automatically.', default=True)
    iface_precompute_cash = fields.Boolean(string='Prefill Cash Payment',  help='The payment input will behave similarily to bank payment input, and will be prefilled with the exact due amount')
    iface_tax_included = fields.Boolean(string='Include Taxes in Prices', help='The displayed prices will always include all taxes, even if the taxes have been setup differently')
    iface_start_categ_id = fields.Many2one('pos.category', string='Start Category', help='The point of sale will display this product category by default. If no category is specified, all available products will be shown')
    iface_display_categ_images = fields.Boolean(string='Display Category Pictures', help="The product categories will be displayed with pictures.")
    receipt_header = fields.Text(string='Receipt Header', help="A short text that will be inserted as a header in the printed receipt")
    receipt_footer = fields.Text(string='Receipt Footer', help="A short text that will be inserted as a footer in the printed receipt")
    proxy_ip = fields.Char(string='IP Address', help='The hostname or ip address of the hardware proxy, Will be autodetected if left empty', size=45)
    state = fields.Selection(POS_CONFIG_STATE, string='Status', required=True, readonly=True, copy=False, default=POS_CONFIG_STATE[0][0])
    uuid = fields.Char(readonly=True, help='A globally unique identifier for this pos configuration, used to prevent conflicts in client-generated data', default=lambda self: str(uuid.uuid4()))
    sequence_id = fields.Many2one(
        'ir.sequence', string='Order IDs Sequence', readonly=True,
        help="This sequence is automatically created by Odoo but you can change it "
        "to customize the reference numbers of your orders.", copy=False)
    session_ids = fields.One2many('pos.session', 'config_id', string='Sessions')
    current_session_id = fields.Many2one('pos.session', compute='_get_current_session', string="Current Session")
    current_session_state = fields.Char(compute='_get_current_session')
    last_session_closing_cash = fields.Float(compute='_get_last_session')
    last_session_closing_date = fields.Date(compute='_get_last_session')
    pos_session_username = fields.Char(compute='_get_current_session_user')
    group_by = fields.Boolean(string='Group Journal Items', help="Check this if you want to group the Journal Items by Product while closing a Session", default=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, default=_default_pricelist)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=_get_default_company)
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', string='Barcodes', help='Defines what kind of barcodes are available and how they are assigned to products, customers and cashiers', required=True, default=_get_default_nomenclature)
    group_pos_manager_id = fields.Many2one(
        'res.groups', string='Point of Sale Manager Group',
        help='This field is there to pass the id of the pos manager group to the point of sale client', default=_get_group_pos_manager)
    group_pos_user_id = fields.Many2one(
        'res.groups', string='Point of Sale User Group',
        help='This field is there to pass the id of the pos user group to the point of sale client', default=_get_group_pos_user)
    tip_product_id = fields.Many2one('product.product', 'Tip Product', help="The product used to encode the customer tip. Leave empty if you do not accept tips.")

    @api.multi
    def _get_currency(self):
        for pos_config in self:
            if pos_config.journal_id:
                currency_id = pos_config.journal_id.currency_id.id or pos_config.journal_id.company_id.currency_id.id
            else:
                currency_id = self.env.user.company_id.currency_id.id
            pos_config.currency_id = currency_id

    @api.multi
    def _get_current_session(self):
        for pos_config in self:
            session = pos_config.session_ids.filtered(lambda r: r.user_id.id == self.env.uid and not r.state == 'closed')
            pos_config.current_session_id = session
            pos_config.current_session_state = session.state

    @api.multi
    def _get_last_session(self):
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
                pos_config.last_session_closing_date = None

    @api.multi
    def _get_current_session_user(self):
        for pos_config in self:
            pos_config.pos_session_username = pos_config.session_ids.filtered(lambda s: s.state == 'opened').user_id.name

    @api.constrains('company_id', 'stock_location_id')
    def _check_company_location(self):
        if self.stock_location_id.company_id and self.stock_location_id.company_id.id != self.company_id.id:
            raise UserError(_("The company of the stock location is different than the one of point of sale"))

    @api.constrains('company_id', 'journal_id')
    def _check_company_journal(self):
        if self.journal_id and self.journal_id.company_id.id != self.company_id.id:
            raise UserError(_("The company of the sale journal is different than the one of point of sale"))

    @api.constrains('company_id', 'journal_ids')
    def _check_company_payment(self):
        journal_ids = [j.id for j in self.journal_ids]
        if self.env['account.journal'].search_count([('id', 'in', journal_ids), ('company_id', '!=', self.company_id.id)]):
            raise UserError(_("The company of a payment method is different than the one of point of sale"))

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        if self.picking_type_id and self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.usage == 'internal' and self.picking_type_id.default_location_dest_id and self.picking_type_id.default_location_dest_id.usage == 'customer':
            self.stock_location_id = self.picking_type_id.default_location_src_id.id

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
        IrSequence = self.env['ir.sequence']
        # force sequence_id field to new pos.order sequence
        values['sequence_id'] = IrSequence.create({
            'name': _('POS Order %s') % values['name'],
            'padding': 4,
            'prefix': _("%s/") % values['name'],
            'code': "pos.order",
            'company_id': values.get('company_id', False),
        }).id

        # TODO master: add field sequence_line_id on model
        # this make sure we always have one available per company
        IrSequence.create({
            'name': _('POS order line %s') % values['name'],
            'padding': 4,
            'prefix': _("%s/") % values['name'],
            'code': "pos.order.line",
            'company_id': values.get('company_id', False),
        })

        return super(PosConfig, self).create(values)

    @api.multi
    def unlink(self):
        for pos_config in self.filtered(lambda pos_config: pos_config.sequence_id):
            pos_config.sequence_id.unlink()
        return super(PosConfig, self).unlink()

    @api.multi
    def set_active(self):
        return self.write({'state': 'active'})

    @api.multi
    def set_inactive(self):
        return self.write({'state': 'inactive'})

    @api.multi
    def set_deprecate(self):
        return self.write({'state': 'deprecated'})

    # Methods to open the POS
    @api.multi
    def open_ui(self):
        self.ensure_one()
        assert len(self.ids) == 1, "you can open only one session at a time"
        return {
            'type': 'ir.actions.act_url',
            'url':   '/pos/web/',
            'target': 'self',
        }

    @api.multi
    def open_existing_session_cb_close(self):
        self.ensure_one()
        assert len(self.ids) == 1, "you can open only one session at a time"
        self.current_session_id.signal_workflow('cashbox_control')
        return self.open_session_cb()

    @api.multi
    def open_session_cb(self):
        self.ensure_one()
        assert len(self.ids) == 1, "you can open only one session at a time"
        if not self.current_session_id:
            values = {
                'user_id': self.env.uid,
                'config_id': self.id,
            }
            self.current_session_id = self.env['pos.session'].create(values)
            if self.current_session_id.state == 'opened':
                return self.open_ui()
            return self._open_session(self.current_session_id.id)
        return self._open_session(self.current_session_id.id)

    @api.multi
    def open_existing_session_cb(self):
        self.ensure_one()
        assert len(self.ids) == 1, "you can open only one session at a time"
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
