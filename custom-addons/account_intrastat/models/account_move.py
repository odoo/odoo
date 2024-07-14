# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class AccountMove(models.Model):
    _inherit = 'account.move'

    intrastat_transport_mode_id = fields.Many2one(
        'account.intrastat.code', string='Intrastat Transport Mode',
        domain="[('type', '=', 'transport')]")

    intrastat_country_id = fields.Many2one('res.country',
        string='Intrastat Country',
        help='Intrastat country, arrival for sales, dispatch for purchases',
        compute='_compute_intrastat_country_id',
        readonly=False,
        store=True,
        domain=[('intrastat', '=', True)])

    def _get_invoice_intrastat_country_id(self):
        ''' Hook allowing to retrieve the intrastat country depending of installed modules.
        :return: A res.country record's id.
        '''
        self.ensure_one()
        if self.is_sale_document():
            if self.partner_shipping_id.country_id.intrastat:
                return self.partner_shipping_id.country_id.id
            else:
                return False
        return self.partner_id.country_id.id

    @api.depends('partner_id', 'partner_shipping_id')
    def _compute_intrastat_country_id(self):
        for move in self:
            if move.partner_id.country_id.intrastat or move.is_sale_document():
                move.intrastat_country_id = move._get_invoice_intrastat_country_id()
            else:
                move.intrastat_country_id = False

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move_line", "intrastat_product_origin_country_id"):
            create_column(self.env.cr, "account_move_line", "intrastat_product_origin_country_id", "int4")
        return super()._auto_init()

    intrastat_transaction_id = fields.Many2one('account.intrastat.code', string='Intrastat', domain="[('type', '=', 'transaction')]", compute='_compute_intrastat_transaction_id', store=True, readonly=False)
    intrastat_product_origin_country_id = fields.Many2one('res.country', string='Product Country', compute='_compute_origin_country', store=True, readonly=False)

    @api.depends('product_id', 'move_id.intrastat_country_id')
    def _compute_origin_country(self):
        for line in self:
            line.intrastat_product_origin_country_id = line.move_id.intrastat_country_id and line.product_id.product_tmpl_id.intrastat_origin_country_id or False

    @api.depends('move_id.move_type', 'move_id.journal_id')
    def _compute_intrastat_transaction_id(self):
        for line in self:
            if line.move_id.intrastat_country_id:
                if line.move_id.move_type in ('in_invoice', 'out_invoice'):
                    line.intrastat_transaction_id = line.move_id.company_id.intrastat_default_invoice_transaction_code_id
                    continue
                elif line.move_id.move_type in ('in_refund', 'out_refund'):
                    line.intrastat_transaction_id = line.move_id.company_id.intrastat_default_refund_transaction_code_id
                    continue
            line.intrastat_transaction_id = None

    # EXTENDS account
    def _get_lock_date_protected_fields(self):
        protected_fields = super()._get_lock_date_protected_fields()
        protected_fields['fiscal'] += ['intrastat_product_origin_country_id', 'intrastat_transaction_id']
        return protected_fields
