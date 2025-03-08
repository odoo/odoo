from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_jo_edi_trade_type = fields.Selection(
        selection=[
            ('local', 'Local Invoice'),
            ('export', 'Export Invoice'),
            ('development', 'Development Area Invoice'),
        ],
        string="JoFotara Invoice type",
        precompute=True,
        compute='_compute_l10n_jo_edi_trade_type',
        store=True, readonly=False,
        copy=False,
        tracking=True,
        required=True,
    )
    l10n_jo_edi_payment_method = fields.Selection(
        selection=[
            ('cash', 'Cash'),
            ('receivable', 'Receivable'),
        ],
        string="JoFotara Payment Method",
        compute='_compute_l10n_jo_edi_payment_method_fields',
        store=True, readonly=False,
        copy=False,
        default='receivable',
        tracking=True,
        required=True,
    )
    l10n_jo_edi_payment_method_readonly = fields.Boolean(compute='_compute_l10n_jo_edi_payment_method_fields')

    @api.depends('invoice_payment_term_id.l10n_jo_edi_cash_payment_method')
    def _compute_l10n_jo_edi_payment_method_fields(self):
        for move in self:
            move.l10n_jo_edi_payment_method_readonly = move.invoice_payment_term_id.l10n_jo_edi_cash_payment_method
            if move.l10n_jo_edi_payment_method_readonly:
                move.l10n_jo_edi_payment_method = 'cash'

    @api.depends('partner_id.country_id.code')
    def _compute_l10n_jo_edi_trade_type(self):
        for move in self:
            if move.partner_id.country_id.code == 'JO':
                move.l10n_jo_edi_trade_type = 'local'
            else:
                move.l10n_jo_edi_trade_type = 'export'

    def _get_invoice_trade_type_code(self):
        return {
            'local': '0',
            'export': '1',
            'development': '2',
        }[self.l10n_jo_edi_trade_type]

    def _get_invoice_payment_method_code(self):
        return {
            'cash': '1',
            'receivable': '2',
        }[self.l10n_jo_edi_payment_method]
