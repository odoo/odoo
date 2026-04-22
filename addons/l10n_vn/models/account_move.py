# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_vn_invoice_number = fields.Char(
        string='E-Invoice Number',
        help='Invoice Number as appearing on the e-invoice.',
        copy=False,
        tracking=True,
    )
    l10n_vn_sinvoice_symbol_usage = fields.Selection(
        selection=[
            ('invoice', 'Invoice'),
            ('vendor_bill', 'Vendor Bill'),
        ],
        compute='_compute_l10n_vn_sinvoice_symbol_usage',
        copy=False,
    )
    l10n_vn_sinvoice_symbol_id = fields.Many2one(
        string='E-Invoice Symbol',
        comodel_name='l10n_vn.sinvoice.symbol',
        compute='_compute_l10n_vn_sinvoice_symbol_id',
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
    )
    l10n_vn_sinvoice_template_code = fields.Char(
        related='l10n_vn_sinvoice_symbol_id.invoice_template_code',
        string='Template Code',
    )

    @api.depends('move_type')
    def _compute_l10n_vn_sinvoice_symbol_usage(self):
        for move in self:
            if move.is_sale_document():
                move.l10n_vn_sinvoice_symbol_usage = 'invoice'
            elif move.is_purchase_document():
                move.l10n_vn_sinvoice_symbol_usage = 'vendor_bill'
            else:
                move.l10n_vn_sinvoice_symbol_usage = False

    @api.depends('company_id', 'journal_id', 'move_type')
    def _compute_l10n_vn_sinvoice_symbol_id(self):
        """ Use the property l10n_vn_symbol_id to set a default invoice symbol. """
        for move in self:
            symbol = move.l10n_vn_sinvoice_symbol_id

            if move.country_code != 'VN':
                move.l10n_vn_sinvoice_symbol_id = False
            elif move.is_sale_document():
                # Use journal's default symbol, fallback to company symbol if not set
                move.l10n_vn_sinvoice_symbol_id = (
                    move.journal_id.l10n_vn_default_invoice_symbol_id
                    or move.company_id.l10n_vn_symbol_id
                    or (symbol if symbol.usage == 'invoice' else False)
                )
            elif move.is_purchase_document():
                move.l10n_vn_sinvoice_symbol_id = symbol if symbol.usage == 'vendor_bill' else False
            else:
                move.l10n_vn_sinvoice_symbol_id = False
