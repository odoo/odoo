from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_jo_edi_invoice_type = fields.Selection(
        selection=[
            ('local', 'Local'),
            ('export', 'Export'),
            ('development', 'Development Area'),
        ],
        string="Invoice Type",
        precompute=True,
        compute='_compute_l10n_jo_edi_invoice_type',
        readonly=False, store=True,
        tracking=True,
        help="Invoice Types as per the Income and Sales Tax Department for JoFotara",
    )
    l10n_jo_edi_payment_method = fields.Selection(
        selection=[
            ('cash', 'Cash'),
            ('receivable', 'Receivable'),
        ],
        string="JoFotara Payment Method",
        default='receivable',
        tracking=True,
        help="Payment Methods as per the Income and Sales Tax Department for JoFotara",
    )
    l10n_jo_edi_state = fields.Selection(selection_add=[('demo', 'Sent (Demo)')])

    @api.depends('partner_id.country_code')
    def _compute_l10n_jo_edi_invoice_type(self):
        for move in self.filtered(lambda m: m.l10n_jo_edi_is_needed and m.l10n_jo_edi_invoice_type != 'development'):
            country_code = move.commercial_partner_id.country_code
            if country_code == 'JO':
                move.l10n_jo_edi_invoice_type = 'local'
            elif country_code:
                move.l10n_jo_edi_invoice_type = 'export'
            else:
                move.l10n_jo_edi_invoice_type = False

    def _l10n_jo_validate_fields(self):
        error_msgs = []
        if not self.l10n_jo_edi_payment_method:
            error_msgs.append(_("Please select a payment method before submission."))
        if not self.l10n_jo_edi_invoice_type:
            error_msgs.append(_("Please select an invoice type before submitting this invoice to JoFotara."))
        error_msgs.append(super()._l10n_jo_validate_fields())
        return "\n".join(error_msgs)

    def _get_invoice_scope_code(self):
        return {
            'local': '0',
            'export': '1',
            'development': '2',
        }.get(self.l10n_jo_edi_invoice_type, '0')

    def _get_invoice_payment_method_code(self):
        return {
            'cash': '1',
            'receivable': '2',
        }.get(self.l10n_jo_edi_payment_method, '2')

    def _send_l10n_jo_edi_request(self, params, headers):
        if self.env.company.l10n_jo_edi_demo_mode:
            return {'EINV_QR': "Demo JoFotara QR"}  # mocked response
        return super()._send_l10n_jo_edi_request(params, headers)

    def _l10n_jo_edi_state_sent_options(self):
        return ['sent', 'demo']

    def _mark_sent_jo_edi(self):
        super()._mark_sent_jo_edi()
        if self.env.company.l10n_jo_edi_demo_mode:
            self.l10n_jo_edi_state = 'demo'
