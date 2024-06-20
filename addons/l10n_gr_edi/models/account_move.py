from odoo import models, fields, _, api
from odoo.addons.l10n_gr_edi.models.classification_data import (
    CLASSIFICATION_CATEGORY_EXPENSE, INVOICE_TYPES_SELECTION, INVOICE_TYPES_HAVE_INCOME, INVOICE_TYPES_HAVE_EXPENSE,
    TYPES_WITH_CORRELATE_INVOICE, COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE, VALID_TAX_AMOUNTS,
    TYPES_WITH_FORBIDDEN_COUNTERPART, TYPES_WITH_VAT_EXEMPT, TYPES_WITH_VAT_CATEGORY_8, TYPES_WITH_FORBIDDEN_PAYMENT, TYPES_WITH_FORBIDDEN_QUANTITY,
)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_gr_edi_mark = fields.Char(string='MyDATA Mark')
    l10n_gr_edi_state = fields.Selection(related='l10n_gr_edi_active_document_id.state', store=True)
    l10n_gr_edi_message = fields.Char(related='l10n_gr_edi_active_document_id.message')
    l10n_gr_edi_warnings = fields.Char(compute='_compute_l10n_gr_edi_warnings')
    l10n_gr_edi_inv_type = fields.Selection(
        selection=INVOICE_TYPES_SELECTION,
        string='MyDATA Invoice Type',
        compute='_compute_l10n_gr_edi_inv_type',
        store=True,
    )
    l10n_gr_edi_available_inv_type = fields.Char(compute='_compute_l10n_gr_edi_available_inv_type')
    l10n_gr_edi_correlation_id = fields.Many2one(
        comodel_name='account.move',
        string='MyDATA Correlated Invoice',
        domain="[('l10n_gr_edi_mark', '!=', False), ('move_type', '=', move_type)]",
    )
    l10n_gr_edi_need_correlated = fields.Boolean(compute='_compute_l10n_gr_edi_need_correlated')
    l10n_gr_edi_document_ids = fields.One2many(
        comodel_name='l10n_gr_edi.document',
        inverse_name='move_id',
        copy=False,
        readonly=True,
    )
    l10n_gr_edi_active_document_id = fields.Many2one(comodel_name='l10n_gr_edi.document')
    l10n_gr_edi_enable_send_invoices = fields.Boolean(compute='_compute_l10n_gr_edi_enable_send')
    l10n_gr_edi_enable_send_expense_classification = fields.Boolean(compute='_compute_l10n_gr_edi_enable_send')

    @api.onchange('l10n_gr_edi_inv_type')
    def _onchange_l10n_gr_edi_inv_type(self):
        for move in self:
            move.l10n_gr_edi_correlation_id = False
            move.invoice_line_ids.l10n_gr_edi_detail_type = False
            move.invoice_line_ids.l10n_gr_edi_cls_vat = False
            for line in move.invoice_line_ids:
                preferred_classification = line._l10n_gr_edi_get_preferred_classification()
                line.l10n_gr_edi_cls_category = preferred_classification.l10n_gr_edi_cls_category
                line.l10n_gr_edi_cls_type = preferred_classification.l10n_gr_edi_cls_type

    @api.depends('l10n_gr_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        """ Prevent user from resetting the move to draft if it's already sent to MyDATA """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_gr_edi_state == 'sent':
                move.show_reset_to_draft_button = False

    @api.depends('move_type')
    def _compute_l10n_gr_edi_inv_type(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                move.l10n_gr_edi_inv_type = '1.1'
            else:
                move.l10n_gr_edi_inv_type = '13.1'

    @api.depends('move_type')
    def _compute_l10n_gr_edi_available_inv_type(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                move.l10n_gr_edi_available_inv_type = ','.join(INVOICE_TYPES_HAVE_INCOME)
            else:
                move.l10n_gr_edi_available_inv_type = ','.join(INVOICE_TYPES_HAVE_EXPENSE)

    @api.depends('l10n_gr_edi_inv_type')
    def _compute_l10n_gr_edi_need_correlated(self):
        for move in self:
            move.l10n_gr_edi_need_correlated = move.l10n_gr_edi_inv_type in TYPES_WITH_CORRELATE_INVOICE

    @api.depends('state')
    def _compute_l10n_gr_edi_warnings(self):
        for move in self:
            if move.state == 'posted':
                warnings = move._l10n_gr_edi_get_errors_pre_request()
                move.l10n_gr_edi_warnings = '\n'.join(warnings)
            else:
                move.l10n_gr_edi_warnings = False

    @api.depends('state', 'l10n_gr_edi_state')
    def _compute_l10n_gr_edi_enable_send(self):
        for move in self:
            have_payment = True
            if move.l10n_gr_edi_inv_type not in TYPES_WITH_FORBIDDEN_PAYMENT:
                reconciled_lines = move.line_ids.filtered(
                    lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
                have_payment = len(reconciled_lines.matched_credit_ids + reconciled_lines.matched_debit_ids) > 0

            move.l10n_gr_edi_enable_send_invoices = all((
                move.country_code == 'GR',
                move.move_type in ('out_invoice', 'out_refund'),
                move.state == 'posted',
                move.l10n_gr_edi_state != 'sent',
                have_payment,
            ))
            move.l10n_gr_edi_enable_send_expense_classification = all((
                move.country_code == 'GR',
                move.move_type in ('in_invoice', 'in_refund'),
                move.state == 'posted',
                move.l10n_gr_edi_state != 'sent',
                have_payment,
            ))

    def _l10n_gr_edi_get_errors_pre_request(self):
        """ Tries to catch all possible errors before sending to MyDATA API """
        self.ensure_one()
        errors = []

        if not self.company_id.l10n_gr_edi_aade_id or not self.company_id.l10n_gr_edi_aade_key:
            errors.append(_('You need to set AADE ID and Key in the company settings.'))
        if not self.l10n_gr_edi_inv_type:
            errors.append(_('Missing MyDATA Invoice Type'))
        if not self.partner_id.vat:
            errors.append(_('Missing VAT on partner %s', self.partner_id.name))
        if not self.company_id.vat:
            errors.append(_('Missing VAT on company %s', self.company_id.name))

        for line in self.invoice_line_ids:
            line_name = line.name or line.id
            if not line.l10n_gr_edi_cls_category and line.l10n_gr_edi_available_cls_category:
                errors.append(_('Missing MyDATA classification category on line %s', line_name))
            if not line.l10n_gr_edi_cls_type \
                    and line.l10n_gr_edi_available_cls_type \
                    and (line.move_id.l10n_gr_edi_inv_type, line.l10n_gr_edi_cls_category) \
                    not in COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE:
                errors.append(_('Missing MyDATA classification type on line %s', line_name))
            if len(line.tax_ids) > 1:
                errors.append(_('MyDATA does not support multiple taxes on line %s', line_name))
            if not line.tax_ids and self.l10n_gr_edi_inv_type not in TYPES_WITH_VAT_CATEGORY_8:
                errors.append(_('Missing tax on line %s', line_name))
            if len(line.tax_ids) == 1 and line.tax_ids.amount == 0 and not line.l10n_gr_edi_tax_exemption_category:
                errors.append(_('Missing MyDATA Tax Exemption Category for line %s', line_name))
            if len(line.tax_ids) == 1 and line.tax_ids.amount not in VALID_TAX_AMOUNTS:
                errors.append(_('Invalid tax amount for line %s. The valid values are %s',
                                line.name, ', '.join(str(tax) for tax in VALID_TAX_AMOUNTS)))
        return errors

    @staticmethod
    def _l10n_gr_edi_get_issuer_counterpart_vals(move):
        party_vals = {
            'issuer_vat': move.company_id.vat,
            'issuer_country': move.company_id.country_code,
            'issuer_branch': len(move.company_id.parent_ids - move.company_id),
        }

        if move.country_code != 'GR':  # issuer not from Greece requires name & address
            party_vals.update({
                'issuer_name': move.company_id.name.encode('utf-8'),
                'issuer_postal_code': move.company_id.zip,
                'issuer_city': move.company_id.city.encode('utf-8'),
            })

        if move.l10n_gr_edi_inv_type not in TYPES_WITH_FORBIDDEN_COUNTERPART:  # some inv_type disallow counterpart
            counterpart_vat = move.partner_id.vat
            party_vals.update({
                'counterpart_vat': counterpart_vat,
                'counterpart_country': move.partner_id.country_code,
                'counterpart_branch': len(move.partner_id.company_id.parent_ids - move.partner_id.company_id),
            })
            if move.partner_id.country_code != 'GR':  # counterpart not from Greece (requires name & address)
                party_vals.update({
                    'counterpart_name': move.partner_id.name.encode('utf-8'),
                    'counterpart_postal_code': move.partner_id.zip,
                    'counterpart_city': move.partner_id.city.encode('utf-8'),
                })

        return party_vals

    @staticmethod
    def _l10n_gr_edi_get_payment_method_vals(move):
        payment_vals = {'payment_details': []}
        reconciled_lines = move.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

        for apr in reconciled_lines.matched_credit_ids:  # for Customer Invoices payment
            payment_vals['payment_details'].append({
                'type': apr.credit_move_id.payment_id.payment_method_line_id.l10n_gr_edi_payment_method_id or '1',
                'amount': apr.debit_amount_currency,
            })
        for apr in reconciled_lines.matched_debit_ids:  # for Credit Notes payment
            payment_vals['payment_details'].append({
                'type': apr.debit_move_id.payment_id.payment_method_line_id.l10n_gr_edi_payment_method_id or '1',
                'amount': apr.credit_amount_currency,
            })

        return payment_vals

    @staticmethod
    def _l10n_gr_edi_get_val_category_vals(line):
        vat_vals = {'vat_category': 8, 'vat_exemption_category': ''}

        if line.tax_ids and line.move_id.l10n_gr_edi_inv_type not in TYPES_WITH_VAT_EXEMPT:
            vat_vals['vat_category'] = {24: 1, 13: 2, 6: 3, 17: 4, 9: 5, 4: 6, 0: 7}[int(line.tax_ids.amount)]

        if vat_vals['vat_category'] == 7 and line.move_id.l10n_gr_edi_inv_type in TYPES_WITH_VAT_CATEGORY_8:
            vat_vals['vat_category'] = 8

        if vat_vals['vat_category'] == 7:
            # need vat exemption category
            vat_vals['vat_exemption_category'] = line.l10n_gr_edi_tax_exemption_category

        return vat_vals

    @staticmethod
    def _l10n_gr_edi_get_classification_vals(line):
        cls_vals = {'ecls': [], 'icls': []}

        if line.l10n_gr_edi_cls_category:
            cls_vals_list = cls_vals['ecls'] if line.l10n_gr_edi_cls_category in CLASSIFICATION_CATEGORY_EXPENSE else cls_vals['icls']
            cls_type = line.l10n_gr_edi_cls_type or ''
            if len(cls_type) > 0 and cls_type[0] == 'X':  # handle duplicate E3 type on inv type 17.5
                cls_type = cls_type[1:]

            cls_vals_list.append({
                'category': line.l10n_gr_edi_cls_category,
                'type': cls_type,
                'amount': abs(line.balance),
            })

            if line.l10n_gr_edi_cls_vat:
                cls_vals_list.append({
                    'category': '',
                    'type': line.l10n_gr_edi_cls_vat,
                    'amount': abs(line.balance),
                })

        return cls_vals

    @staticmethod
    def _l10n_gr_edi_get_sum_classification_vals(details):
        icls_vals, ecls_vals = {}, {}
        summary_icls, summary_ecls = [], []

        for detail in details:
            icls_list, ecls_list = detail['icls'], detail['ecls']
            for icls in icls_list:
                category_type = (icls['category'], icls['type'])
                icls_vals.setdefault(category_type, 0)
                icls_vals[category_type] += icls['amount']
            for ecls in ecls_list:
                category_type = (ecls['category'], ecls['type'])
                ecls_vals.setdefault(category_type, 0)
                ecls_vals[category_type] += ecls['amount']

        for category_type, amount in icls_vals.items():
            category, cls_type = category_type
            summary_icls.append({'type': cls_type, 'category': category, 'amount': amount})
        for category_type, amount in ecls_vals.items():
            category, cls_type = category_type
            summary_ecls.append({'type': cls_type, 'category': category, 'amount': amount})

        return {'summary_icls': summary_icls, 'summary_ecls': summary_ecls}

    @staticmethod
    def _l10n_gr_edi_cleanup_xml_vals(xml_value):
        """ Remove empty string and list value from xml_vals """
        if isinstance(xml_value, list):
            return [AccountMove._l10n_gr_edi_cleanup_xml_vals(item) for item in xml_value if item not in ('', [])]
        elif isinstance(xml_value, dict):
            return {k: AccountMove._l10n_gr_edi_cleanup_xml_vals(v) for k, v in xml_value.items() if v not in ('', [])}
        else:
            return xml_value

    def _l10n_gr_edi_prepare_invoice_xml_vals(self):
        xml_vals = {'invoices': []}

        for move in self:
            details = []
            for line in move.line_ids.filtered(lambda l: l.display_type == 'product'):
                details.append({
                    'line_number': len(details) + 1,
                    'quantity': line.quantity if move.l10n_gr_edi_inv_type not in TYPES_WITH_FORBIDDEN_QUANTITY else '',
                    'detail_type': line.l10n_gr_edi_detail_type or '',
                    'net_value': abs(line.balance),
                    'vat_amount': round(line.price_total - line.price_subtotal, 2),
                    **self._l10n_gr_edi_get_val_category_vals(line),
                    **self._l10n_gr_edi_get_classification_vals(line),
                })

            xml_vals['invoices'].append({
                'header_series': '_'.join(move.name.split('/')[:-1]),
                'header_aa': move.name.split('/')[-1],
                'header_issue_date': move.date.isoformat(),
                'header_invoice_type': move.l10n_gr_edi_inv_type,
                'header_currency': move.currency_id.name,
                'header_correlate': move.l10n_gr_edi_correlation_id.l10n_gr_edi_mark or '',
                'details': details,
                'summary_total_net_value': move.amount_untaxed,
                'summary_total_vat_amount': move.amount_tax,
                'summary_total_withheld_amount': 0,
                'summary_total_fees_amount': 0,
                'summary_total_stamp_duty_amount': 0,
                'summary_total_other_taxes_amount': 0,
                'summary_total_deductions_amount': 0,
                'summary_total_gross_value': move.amount_total,
                **self._l10n_gr_edi_get_issuer_counterpart_vals(move),
                **self._l10n_gr_edi_get_payment_method_vals(move),
                **self._l10n_gr_edi_get_sum_classification_vals(details),
            })

        xml_vals = self._l10n_gr_edi_cleanup_xml_vals(xml_vals)
        return xml_vals

    def _l10n_gr_edi_prepare_expense_classification_xml_vals(self):
        xml_vals = {'invoices': []}

        for move in self:
            details = []
            for line in move.line_ids.filtered(lambda l: l.display_type == 'product'):
                details.append({
                    'line_number': len(details) + 1,
                    **self._l10n_gr_edi_get_classification_vals(line),
                })

            xml_vals['invoices'].append({
                'mark': move.l10n_gr_edi_mark,
                'transaction_mode': '',  # Later, add a way to 'reject' received invoices
                'details': details,
            })

        xml_vals = self._l10n_gr_edi_cleanup_xml_vals(xml_vals)
        return xml_vals

    def l10n_gr_edi_send_invoices(self):
        """ Create Document(s) of XML values from selected invoice(s) and send them to MyDATA """
        xml_vals = self._l10n_gr_edi_prepare_invoice_xml_vals()
        document_ids = self.env['l10n_gr_edi.document'].create([{'move_id': move.id} for move in self])
        document_ids._send_mydata_invoices_xml(xml_vals)

    def l10n_gr_edi_send_expense_classification(self):
        """ Create XML documents for Expense Classifications and send them to MyDATA """
        xml_vals = self._l10n_gr_edi_prepare_expense_classification_xml_vals()
        document_ids = self.env['l10n_gr_edi.document'].create([{'move_id': move.id} for move in self])
        document_ids._send_mydata_expense_classifications_xml(xml_vals)

    def _l10n_gr_edi_try_send(self, send_expense_classification=False):
        """ Gather all invoices in `self` and compute errors in each of them.
         Collect all 'good' invoices and send them as batches to MyDATA.
         Any errors detected will not be raised but instead saved as a new document.
         @param send_expense_classification: False (default, send invoice) | True (send expense classification) """
        moves_to_send = self.env['account.move']
        for move in self:
            if errors := move._l10n_gr_edi_get_errors_pre_request():
                self.env['l10n_gr_edi.document'].create([{
                    'move_id': move.id,
                    'state': 'error',
                    'message': '\n'.join(errors),
                    'datetime': fields.Datetime.now(),
                }])
            else:
                moves_to_send |= move

        if moves_to_send:
            if send_expense_classification:
                moves_to_send.l10n_gr_edi_send_expense_classification()
            else:
                moves_to_send.l10n_gr_edi_send_invoices()

    def l10n_gr_edi_try_send_invoices(self):
        self._l10n_gr_edi_try_send()

    def l10n_gr_edi_try_send_expense_classification(self):
        self._l10n_gr_edi_try_send(send_expense_classification=True)
