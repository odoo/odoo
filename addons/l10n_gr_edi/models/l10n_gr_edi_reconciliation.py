from odoo import api, fields, models
from odoo.exceptions import UserError


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

    def _l10n_gr_edi_find_xml_value(self, element, name):
        return element.xpath(f'string(./*[local-name()="{name}"])')

    @api.model
    def _l10n_gr_edi_parse_counterparty_documents(self, root):
        events_by_mark = {}
        for event in root.xpath('//*[local-name()="expensesInvoiceClassification"]'):
            transaction_mode = self._l10n_gr_edi_find_xml_value(event, 'transactionMode')
            # If it's not a rejection "1" nor a deviation "2" just skip as we don't change anything
            if transaction_mode not in ('1', '2'):
                continue

            invoice_mark = self._l10n_gr_edi_find_xml_value(event, 'invoiceMark')
            events_by_mark[invoice_mark] = {
                'classification_mark': self._l10n_gr_edi_find_xml_value(event, 'classificationMark'),
                'state': 'rejected' if transaction_mode == '1' else 'deviation',
            }

        return events_by_mark

    @api.model
    def _l10n_gr_edi_prepare_reconciliation_values(self, company, invoice_element, move, currencies):
        headers = invoice_element.xpath('./*[local-name()="invoiceHeader"]')
        summaries = invoice_element.xpath('./*[local-name()="invoiceSummary"]')
        if not headers or not summaries:
            raise UserError(self.env._('The myDATA invoice is missing required header or summary information.'))
        header, summary = headers[0], summaries[0]
        counterpart = invoice_element.xpath('./*[local-name()="counterpart"]')
        counterpart_vat = self._l10n_gr_edi_find_xml_value(counterpart[0], 'vatNumber') if counterpart else False
        currency_name = self._l10n_gr_edi_find_xml_value(header, 'currency') or 'EUR'
        currency = currencies.get(currency_name)

        return {
            'company_id': company.id,
            'move_id': move.id if move else False,
            'partner_id': move.partner_id.id if move else False,
            'currency_id': currency.id,
            'mark': self._l10n_gr_edi_find_xml_value(invoice_element, 'mark'),
            'uid': self._l10n_gr_edi_find_xml_value(invoice_element, 'uid'),
            'qr_url': self._l10n_gr_edi_find_xml_value(invoice_element, 'qrCodeUrl'),
            'aade_invoice_series': self._l10n_gr_edi_find_xml_value(header, 'series'),
            'aade_invoice_number': self._l10n_gr_edi_find_xml_value(header, 'aa'),
            'aade_invoice_date': fields.Date.to_date(self._l10n_gr_edi_find_xml_value(header, 'issueDate')),
            'aade_invoice_type': self._l10n_gr_edi_find_xml_value(header, 'invoiceType'),
            'aade_counterpart_vat': counterpart_vat,
            'aade_amount_untaxed': float(self._l10n_gr_edi_find_xml_value(summary, 'totalNetValue')),
            'aade_amount_tax': float(self._l10n_gr_edi_find_xml_value(summary, 'totalVatAmount')),
            'aade_amount_total': float(self._l10n_gr_edi_find_xml_value(summary, 'totalGrossValue')),
        }

    @api.model
    def _l10n_gr_edi_sync_transmitted_documents(self, company, root):
        invoices = root.xpath('//*[local-name()="invoice"]')
        if not invoices:
            return
        marks = [invoice.xpath('string(./*[local-name()="mark"])') for invoice in invoices]
        currency_names = {
            invoice.xpath('string(./*[local-name()="invoiceHeader"]/*[local-name()="currency"])') or 'EUR'
            for invoice in invoices
        }
        currencies = {
            currency.name: currency
            for currency in self.env['res.currency'].with_context(active_test=False).search([
                ('name', 'in', currency_names),
            ])
        }
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
                moves_by_mark.get(mark),
                currencies,
            )
            if reconciliation := existing_by_mark.get(mark):
                reconciliation.write(values)
            else:
                create_values.append({
                    **values,
                    'state': 'no_exception',
                })

        if create_values:
            self.create(create_values)

    @api.model
    def _l10n_gr_edi_sync_counterparty_documents(self, company, root):
        events_by_mark = self._l10n_gr_edi_parse_counterparty_documents(root)
        reconciliations_by_mark = {
            reconciliation.mark: reconciliation
            for reconciliation in self.search([
                ('company_id', '=', company.id),
                ('mark', 'in', list(events_by_mark)),
            ])
        }

        for invoice_mark, event in events_by_mark.items():
            if reconciliation := reconciliations_by_mark.get(invoice_mark):
                reconciliation.write(event)
