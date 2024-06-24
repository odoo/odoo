from lxml import etree

from odoo import models, fields, _, api
from odoo.addons.l10n_gr_edi.models.classification_data import (
    CLASSIFICATION_CATEGORY_EXPENSE, INVOICE_TYPES_SELECTION, INVOICE_TYPES_HAVE_INCOME, INVOICE_TYPES_HAVE_EXPENSE,
    TYPES_WITH_CORRELATE_INVOICE, COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE, VALID_TAX_AMOUNTS,
    TYPES_WITH_FORBIDDEN_COUNTERPART, TYPES_WITH_VAT_EXEMPT, TYPES_WITH_VAT_CATEGORY_8, TYPES_WITH_FORBIDDEN_PAYMENT, TYPES_WITH_FORBIDDEN_QUANTITY,
)
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_gr_edi_mark = fields.Char(string='MyDATA Mark')
    l10n_gr_edi_document_ids = fields.One2many(
        comodel_name='l10n_gr_edi.document',
        inverse_name='move_id',
        copy=False,
        readonly=True,
    )
    l10n_gr_edi_state = fields.Selection(
        selection=[('move_sent', 'Sent'), ('move_error', 'Error')],
        compute='_compute_l10n_gr_edi_state',
        store=True,
    )
    l10n_gr_edi_available_inv_type = fields.Char(compute='_compute_l10n_gr_edi_available_inv_type')
    l10n_gr_edi_inv_type = fields.Selection(
        selection=INVOICE_TYPES_SELECTION,
        string='MyDATA Invoice Type',
        compute='_compute_l10n_gr_edi_inv_type',
        store=True,
    )
    l10n_gr_edi_correlation_id = fields.Many2one(
        comodel_name='account.move',
        string='MyDATA Correlated Invoice',
        domain="[('l10n_gr_edi_mark', '!=', False), ('move_type', '=', move_type)]",
    )
    l10n_gr_edi_warnings = fields.Char(compute='_compute_l10n_gr_edi_warnings')
    l10n_gr_edi_need_correlated = fields.Boolean(compute='_compute_l10n_gr_edi_need_correlated')
    l10n_gr_edi_enable_send_invoices = fields.Boolean(compute='_compute_l10n_gr_edi_enable_send')
    l10n_gr_edi_enable_send_expense_classification = fields.Boolean(compute='_compute_l10n_gr_edi_enable_send')

    ################################################################################
    # Standard Field Computes
    ################################################################################

    @api.depends('l10n_gr_edi_document_ids')
    def _compute_l10n_gr_edi_state(self):
        for move in self:
            if gr_documents := move.l10n_gr_edi_document_ids.sorted():
                move.l10n_gr_edi_state = gr_documents[0].state
            else:
                move.l10n_gr_edi_state = False

    @api.depends('l10n_gr_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        """ Prevent user from resetting the move to draft if it's already sent to MyDATA """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_gr_edi_state == 'move_sent':
                move.show_reset_to_draft_button = False

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
                move.l10n_gr_edi_state != 'move_sent',
                have_payment,
            ))
            move.l10n_gr_edi_enable_send_expense_classification = all((
                move.country_code == 'GR',
                move.move_type in ('in_invoice', 'in_refund'),
                move.state == 'posted',
                move.l10n_gr_edi_state != 'move_sent',
                have_payment,
            ))

    ################################################################################
    # Dynamic Selection Field Computes
    ################################################################################

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

    ################################################################################
    # Greece Document Handler
    ################################################################################

    @api.model
    def _l10n_gr_edi_document_create_attachment(self, document, move_id, xml_content):
        document.attachment_id = self.env['ir.attachment'].sudo().create({
            'name': self._l10n_gr_edi_get_attachment_file_name(move_id),
            'raw': xml_content,
            'res_model': self._name,
            'res_id': document.id,
            'type': 'binary',
            'mimetype': 'application/xml',
        })

    @api.model
    def _l10n_gr_edi_create_document_move_error(self, move_id, message, xml_content=''):
        document = self.env['l10n_gr_edi.document'].create({
            'move_id': move_id,
            'state': 'move_error',
            'message': message,
        })
        if xml_content:
            self._l10n_gr_edi_document_create_attachment(document, move_id, xml_content)

    @api.model
    def _l10n_gr_edi_create_document_move_sent(self, move_id, xml_content):
        document = self.env['l10n_gr_edi.document'].create({
            'move_id': move_id,
            'state': 'move_sent',
        })
        self._l10n_gr_edi_document_create_attachment(document, move_id, xml_content)

    ################################################################################
    # Helpers
    ################################################################################

    @api.model
    def _l10n_gr_edi_get_attachment_file_name(self, move_id: int):
        move = self.browse(move_id)
        return f"mydata_{move.name.replace('/', '_')}.xml"

    @api.model
    def _l10n_gr_edi_cleanup_xml_vals(self, xml_vals):
        """ Recursively remove empty string <''> and empty list <[]> from xml_vals """
        if isinstance(xml_vals, list):
            return [self._l10n_gr_edi_cleanup_xml_vals(item) for item in xml_vals if item not in ('', [])]
        elif isinstance(xml_vals, dict):
            return {k: self._l10n_gr_edi_cleanup_xml_vals(v) for k, v in xml_vals.items() if v not in ('', [])}
        else:
            return xml_vals

    @api.model
    def _l10n_gr_edi_generate_xml_content(self, xml_vals, send_classification=False):
        xml_template = 'l10n_gr_edi.send_invoice' if not send_classification else \
                       'l10n_gr_edi.send_expense_classification'
        xml_content = self.env['ir.qweb']._render(xml_template, xml_vals)
        xml_content = etree.tostring(cleanup_xml_node(xml_content), encoding='ISO-8859-7', standalone='yes')
        xml_content = xml_content.decode('iso8859_7')
        return xml_content

    @api.model
    def _l10n_gr_edi_create_move_xml_map(self, xml_vals):
        move_xml_map: dict[int, str] = {}

        for invoice_vals in xml_vals['invoices']:
            single_xml_vals = {'invoices': [invoice_vals]}
            xml_content = self._l10n_gr_edi_generate_xml_content(single_xml_vals)
            move_xml_map[invoice_vals['__id__']] = xml_content

        return move_xml_map

    ################################################################################
    # Prepare XML Values
    ################################################################################

    @api.model
    def _l10n_gr_edi_get_issuer_counterpart_vals(self, move):
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

    @api.model
    def _l10n_gr_edi_get_payment_method_vals(self, move):
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

    @api.model
    def _l10n_gr_edi_get_val_category_vals(self, line):
        vat_vals = {'vat_category': 8, 'vat_exemption_category': ''}

        if line.tax_ids and line.move_id.l10n_gr_edi_inv_type not in TYPES_WITH_VAT_EXEMPT:
            vat_vals['vat_category'] = {24: 1, 13: 2, 6: 3, 17: 4, 9: 5, 4: 6, 0: 7}[int(line.tax_ids.amount)]

        if vat_vals['vat_category'] == 7 and line.move_id.l10n_gr_edi_inv_type in TYPES_WITH_VAT_CATEGORY_8:
            vat_vals['vat_category'] = 8

        if vat_vals['vat_category'] == 7:
            # need vat exemption category
            vat_vals['vat_exemption_category'] = line.l10n_gr_edi_tax_exemption_category

        return vat_vals

    @api.model
    def _l10n_gr_edi_get_classification_vals(self, line):
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

    @api.model
    def _l10n_gr_edi_get_sum_classification_vals(self, details):
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

    def _l10n_gr_edi_get_invoices_xml_vals(self):
        xml_vals = {'invoices': []}

        for move in self.sorted(key='id'):
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
                '__id__': move.id,  # will not be rendered; for creating {move_id -> move_xml} mapping
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

    def _l10n_gr_edi_get_expense_classification_xml_vals(self):
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

    ################################################################################
    # Send Logics
    ################################################################################

    def _l10n_gr_edi_get_errors_pre_request(self):
        """ Try to catch all possible errors before sending to MyDATA. """
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

    @api.model
    def _l10n_gr_edi_handle_send_result(self, result, xml_vals):
        """ Handle the result object received from sending xml to myDATA.
            Create the related error/sent document with the necessary values. """
        move_xml_map = self._l10n_gr_edi_create_move_xml_map(xml_vals)
        move_ids = list(move_xml_map.keys())
        id_move_map = {move.id: move for move in self}

        if 'error' in result:
            # If the request failed at this stage, it is probably caused by connection/credentials issues.
            # In such case, we don't need to attach the xml here as it won't be helpful for the user.
            for move_id in move_ids:
                self._l10n_gr_edi_create_document_move_error(move_id, result['error'])
            return

        for result_id, result_dict in result.items():
            move_id = move_ids[result_id]
            move = id_move_map[move_id]
            xml_content = move_xml_map[move_id]
            if 'error' in result_dict:
                # In this stage, the sending process has succeeded, and any error we receive is generated from the API.
                # Previous error(s) without attachments (generated from pre-compute) are now useless and can be unlinked.
                move.l10n_gr_edi_document_ids.filtered(lambda d: d.state == 'move_error' and not d.attachment_id).unlink()
                self._l10n_gr_edi_create_document_move_error(move_id, result_dict['error'], xml_content)
            else:
                move.l10n_gr_edi_mark = result_dict['l10n_gr_edi_mark']
                move.l10n_gr_edi_document_ids.filtered(lambda d: d.state == 'move_error').unlink()
                self._l10n_gr_edi_create_document_move_sent(move_id, xml_content)

    def _l10n_gr_edi_send_invoices(self):
        """ Send batch of invoices SendInvoice XML to MyDATA. """
        xml_vals = self._l10n_gr_edi_get_invoices_xml_vals()
        xml_content = self._l10n_gr_edi_generate_xml_content(xml_vals)
        result = self.env['l10n_gr_edi.document']._make_mydata_request(
            company=self.company_id,
            endpoint='SendInvoices',
            xml_content=xml_content,
        )
        self._l10n_gr_edi_handle_send_result(result, xml_vals)

    def _l10n_gr_edi_send_expense_classification(self):
        """ Send batch of invoices SendExpensesClassification XML to MyDATA. """
        xml_vals = self._l10n_gr_edi_get_expense_classification_xml_vals()
        xml_content = self._l10n_gr_edi_generate_xml_content(xml_vals)
        result = self.env['l10n_gr_edi.document']._make_mydata_request(
            company=self.company_id,
            endpoint='SendExpensesClassification',
            xml_content=xml_content,
        )
        self._l10n_gr_edi_handle_send_result(result, xml_vals)

    def _l10n_gr_edi_get_moves_to_send(self):
        """ This method pre-compute the errors in each of move inside `self` and returns the "good" move(s).
            If we only send one move (the most common scenario), any errors detected will be raised immediately.
            Otherwise, an error document will be created on each problematic move(s).
            The problematic move(s) will not be returned. """
        moves_to_send = self.env['account.move']
        for move in self:
            if errors := move._l10n_gr_edi_get_errors_pre_request():
                if len(self) == 1:
                    raise UserError('\n'.join(errors))
                self._l10n_gr_edi_create_document_move_error(move.id, '\n'.join(errors))
            else:
                moves_to_send |= move
        return moves_to_send

    def _l10n_gr_edi_handle_raise_error(self):
        """ If error message is found on the invoice's document, raise an error. """
        self.ensure_one()
        if error_message := self.l10n_gr_edi_document_ids.sorted()[0].message:
            self.env.cr.commit()  # Save the created document(s) before raising error
            raise UserError(error_message)

    def l10n_gr_edi_try_send_invoices(self):
        moves_to_send = self._l10n_gr_edi_get_moves_to_send()
        if moves_to_send:
            moves_to_send._l10n_gr_edi_send_invoices()
            if len(self) == 1:
                moves_to_send._l10n_gr_edi_handle_raise_error()

    def l10n_gr_edi_try_send_expense_classification(self):
        moves_to_send = self._l10n_gr_edi_get_moves_to_send()
        if moves_to_send:
            moves_to_send._l10n_gr_edi_send_expense_classification()
            if len(self) == 1:
                moves_to_send._l10n_gr_edi_handle_raise_error()
