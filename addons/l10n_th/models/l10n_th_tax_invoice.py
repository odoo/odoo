from odoo import api, fields, models


class L10nThTaxInvoice(models.Model):
    _name = 'l10n_th.tax.invoice'
    _description = 'Tax Invoice Information'
    _check_company_auto = True

    invoice_move_id = fields.Many2one(
        comodel_name='account.move',
        required=True, ondelete='cascade',
        check_company=True,
    )
    payment_move_id = fields.Many2one(
        comodel_name='account.move',
        ondelete='set null',
        check_company=True,
    )

    date = fields.Date(string="Date")
    tax_invoice_number = fields.Char(string="Tax Invoice Number")
    reference = fields.Char(string="Reference")
    total_amount = fields.Monetary(string='Total Amount')
    vat_amount = fields.Monetary(string='VAT Amount')
    amount_residual = fields.Monetary(string='Amount Due')
    tax_group_amounts = fields.Json(
        string="Tax Group Amounts",
        copy=False,
    )
    tax_invoice_lines = fields.Json(
        string="Tax Invoice Lines",
        copy=False,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        default='draft',
    )
    currency_id = fields.Many2one(related='invoice_move_id.currency_id')
    company_id = fields.Many2one(
        related='invoice_move_id.company_id',
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )

    def _get_tax_invoice_document_title(self):
        self.ensure_one()

        doc_name = self.tax_invoice_number

        if self.reference:
            doc_name = self.env._("Receipt / Tax Invoice %(doc_name)s", doc_name=doc_name)
        else:
            doc_name = self.env._("Tax Invoice %(doc_name)s", doc_name=doc_name)

        if self.state != 'posted':
            if self.state == 'draft':
                doc_name = self.env._("Draft %(doc_name)s", doc_name=doc_name)
            if self.state == 'cancel':
                doc_name = self.env._("Cancelled %(doc_name)s", doc_name=doc_name)

        return doc_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tax_invoice_number'):
                vals['tax_invoice_number'] = self.env['ir.sequence'].next_by_code(
                    'l10n_th.tax.invoice.receipt_tax_invoice_number'
                    if vals.get('payment_move_id')
                    else 'l10n_th.tax.invoice.tax_invoice_number',
                    sequence_date=vals['date'] if vals['date'] else None,
                )

        return super().create(vals_list)

    def action_print_tax_invoice_pdf(self):
        self.ensure_one()
        return self.env.ref('l10n_th.action_report_tax_invoice').report_action(self.ids, config=False)
