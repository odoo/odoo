# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from dateutil import parser


class PosOrderLineProForma(models.Model):
    _name = 'pos.order_line_pro_forma'
    _inherit = 'pos.order.line'
    _description = 'Order line of a pro forma order'

    order_id = fields.Many2one('pos.order_pro_forma')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_id') and not vals.get('name'):
                # set name based on the sequence specified on the config
                config = self.env['pos.order'].browse(vals['order_id']).session_id.config_id
                if config.profo_sequence_line_id:
                    vals['name'] = config.profo_sequence_line_id._next()
        return super().create(vals_list)


class PosOrderProForma(models.Model):
    _name = 'pos.order_pro_forma'
    _description = 'Model for pro forma order'

    def _default_session(self):
        so = self.env['pos.session']
        session_ids = so.search([('state', '=', 'opened'), ('user_id', '=', self.env.uid)])
        return session_ids and session_ids[0] or False

    def _default_pricelist(self):
        session_ids = self._default_session()
        if session_ids:
            session_record = self.env['pos.session'].browse(session_ids.id)
            return session_record.config_id.pricelist_id or False
        return False

    name = fields.Char('Order Ref', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.users'].browse(self.env.uid).company_id.id, readonly=True)
    date_order = fields.Datetime('Order Date', readonly=True)
    create_date = fields.Datetime(string="Pro Forma Creation")
    user_id = fields.Many2one('res.users', 'Salesman', help="Person who uses the cash register. It can be a reliever, a student or an interim employee.", readonly=True)
    amount_total = fields.Float(readonly=True)
    lines = fields.One2many('pos.order_line_pro_forma', 'order_id', 'Order Lines', readonly=True, copy=True)
    pos_reference = fields.Char('Receipt Ref', readonly=True)
    session_id = fields.Many2one('pos.session', 'Session', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    config_id = fields.Many2one('pos.config', related='session_id.config_id', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', default=_default_pricelist, readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', 'Fiscal Position', readonly=True)
    currency_id = fields.Many2one(related='session_id.currency_id')
    amount_total = fields.Float(readonly=True)
    amount_tax = fields.Float(string='Taxes', digits=0, readonly=True, required=True)
    table_id = fields.Many2one('restaurant.table', 'Table', readonly=True)

    def set_values(self, ui_order):
        return {
            'user_id': ui_order['user_id'] or False,
            'session_id': ui_order['pos_session_id'],
            'pos_reference': ui_order['name'],
            'lines': [self.env['pos.order_line_pro_forma']._order_line_fields(l, ui_order['pos_session_id']) for l in ui_order['lines']] if ui_order['lines'] else False,
            'partner_id': ui_order['partner_id'] or False,
            'date_order': parser.parse(ui_order['creation_date']).strftime("%Y-%m-%d %H:%M:%S"),
            'amount_total': ui_order.get('amount_total'),
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'table_id': ui_order.get('table_id'),
            'amount_tax': ui_order.get('amount_tax')
        }

    @api.model
    def create_from_ui(self, orders):
        for ui_order in orders:
            values = self.set_values(ui_order)
            session = self.env['pos.session'].browse(values['session_id'])
            values['name'] = session.config_id.profo_sequence_id._next()

            self.create(values)
