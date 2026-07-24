from odoo import api, fields, models


class L10nGrEdiReconciliation(models.Model):
    _name = 'l10n_gr_edi.reconciliation'
    _description = 'myDATA Reconciliation'
    _rec_name = 'mark'

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice',
    )
    partner_id = fields.Many2one(comodel_name='res.partner')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
    )

    mark = fields.Char(
        string='Invoice MARK',
        required=True,
    )
    uid = fields.Char(string='UID')
    qr_url = fields.Char(string='QR URL')
    aade_invoice_series = fields.Char(string='AADE Invoice Series')
    aade_invoice_number = fields.Char(string='AADE Invoice Number')
    aade_invoice_date = fields.Date(string='AADE Invoice Date')
    aade_invoice_type = fields.Char(string='AADE Invoice Type')
    aade_counterpart_vat = fields.Char(string='AADE Counterpart VAT')
    aade_amount_untaxed = fields.Monetary(string='AADE Untaxed Amount', currency_field='currency_id')
    aade_amount_tax = fields.Monetary(string='AADE VAT Amount', currency_field='currency_id')
    aade_amount_total = fields.Monetary(string='AADE Total', currency_field='currency_id')

    classification_mark = fields.Char(string='Counterparty Response MARK')

    state = fields.Selection(
        selection=[
            ('no_exception', 'No Exception Reported'),
            ('rejected', 'Rejected'),
            ('deviation', 'Deviation'),
        ],
        string='Reconciliation Status',
        required=True,
        help=(
            "'No Exception Reported' means only that no rejection or deviation reported; "
            "it doesn't necessarily mean that the counterparty has reviewed the invoice."
        ),
    )
    sync_datetime = fields.Datetime(string='Last Sync')

    _unique_company_mark = models.Constraint(
        'unique(company_id, mark)',
        'A myDATA reconciliation record already exists for this company and invoice MARK.',
    )

    def action_sync(self):
        self.env.company._l10n_gr_edi_sync_reconciliation()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def _l10n_gr_edi_parse_counterparty_documents(self, roots):
        def find_value(element, name):
            return element.xpath(f'string(./*[local-name()="{name}"])')

        events_by_mark = {}
        for root in roots:
            for event in root.xpath('//*[local-name()="expensesInvoiceClassification"]'):
                transaction_mode = find_value(event, 'transactionMode')
                if transaction_mode not in ('1', '2'):
                    continue

                invoice_mark = find_value(event, 'invoiceMark')
                events_by_mark[invoice_mark] = {
                    'classification_mark': find_value(event, 'classificationMark'),
                    'state': 'rejected' if transaction_mode == '1' else 'deviation',
                }

        return events_by_mark

    @api.model
    def _l10n_gr_edi_prepare_reconciliation_values(self, company, invoice, event, move, sync_datetime):
        def find_value(element, xpath):
            return element.xpath(f'string({xpath})')

        header = invoice.xpath('./*[local-name()="invoiceHeader"]')[0]
        summary = invoice.xpath('./*[local-name()="invoiceSummary"]')[0]
        counterpart = invoice.xpath('./*[local-name()="counterpart"]')
        counterpart_vat = find_value(counterpart[0], './*[local-name()="vatNumber"]') if counterpart else False
        currency_name = find_value(header, './*[local-name()="currency"]') or 'EUR'
        currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', currency_name)],
            limit=1,
        )

        return {
            'company_id': company.id,
            'move_id': move.id if move else False,
            'partner_id': move.partner_id.id if move else False,
            'currency_id': currency.id,
            'mark': find_value(invoice, './*[local-name()="mark"]'),
            'uid': find_value(invoice, './*[local-name()="uid"]'),
            'qr_url': find_value(invoice, './*[local-name()="qrCodeUrl"]'),
            'aade_invoice_series': find_value(header, './*[local-name()="series"]'),
            'aade_invoice_number': find_value(header, './*[local-name()="aa"]'),
            'aade_invoice_date': fields.Date.to_date(find_value(header, './*[local-name()="issueDate"]')),
            'aade_invoice_type': find_value(header, './*[local-name()="invoiceType"]'),
            'aade_counterpart_vat': counterpart_vat,
            'aade_amount_untaxed': float(find_value(summary, './*[local-name()="totalNetValue"]')),
            'aade_amount_tax': float(find_value(summary, './*[local-name()="totalVatAmount"]')),
            'aade_amount_total': float(find_value(summary, './*[local-name()="totalGrossValue"]')),
            'classification_mark': event.get('classification_mark'),
            'state': event.get('state', 'no_exception'),
            'sync_datetime': sync_datetime,
        }

    @api.model
    def _l10n_gr_edi_sync_documents(self, company, transmitted_roots, counterparty_roots, sync_datetime):
        events_by_mark = self._l10n_gr_edi_parse_counterparty_documents(counterparty_roots)
        invoices = [
            invoice
            for root in transmitted_roots
            for invoice in root.xpath('//*[local-name()="invoice"]')
        ]
        marks = [invoice.xpath('string(./*[local-name()="mark"])') for invoice in invoices]
        moves_by_mark = {
            move.l10n_gr_edi_mark: move
            for move in self.env['account.move'].search([
                ('company_id', '=', company.id),
                ('l10n_gr_edi_mark', 'in', marks),
            ])
        }
        existing_by_mark = {
            reconciliation.mark: reconciliation
            for reconciliation in self.search([
                ('company_id', '=', company.id),
                ('mark', 'in', marks),
            ])
        }

        create_values = []
        for invoice, mark in zip(invoices, marks):
            values = self._l10n_gr_edi_prepare_reconciliation_values(
                company,
                invoice,
                events_by_mark.get(mark, {}),
                moves_by_mark.get(mark),
                sync_datetime,
            )
            if reconciliation := existing_by_mark.get(mark):
                reconciliation.write(values)
            else:
                create_values.append(values)

        if create_values:
            self.create(create_values)
