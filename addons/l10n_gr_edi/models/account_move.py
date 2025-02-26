from lxml import etree

from odoo import models, fields, _, api
from odoo.addons.l10n_gr_edi.models.classification_data import (
    CLASSIFICATION_CATEGORY_EXPENSE, INVOICE_TYPES_SELECTION, INVOICE_TYPES_HAVE_INCOME, INVOICE_TYPES_HAVE_EXPENSE, PAYMENT_METHOD_SELECTION,
    TYPES_WITH_CORRELATE_INVOICE, COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE, VALID_TAX_AMOUNTS, TYPES_WITH_MANDATORY_COUNTERPART, TYPES_WITH_MANDATORY_PAYMENT,
    TYPES_WITH_FORBIDDEN_COUNTERPART, TYPES_WITH_VAT_EXEMPT, TYPES_WITH_VAT_CATEGORY_8, TYPES_WITH_FORBIDDEN_QUANTITY,
)
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_gr_edi_mark = fields.Char(string='MyDATA Mark')
    l10n_gr_edi_cls_mark = fields.Char(string='MyDATA Classification Mark')
    l10n_gr_edi_document_ids = fields.One2many(
        comodel_name='l10n_gr_edi.document',
        inverse_name='move_id',
        copy=False,
        readonly=True,
    )
    l10n_gr_edi_state = fields.Selection(
        selection=[('move_sent', 'Sent'), ('move_error', 'Error')],
        string='MyDATA Status',
        compute='_compute_l10n_gr_edi_state',
        store=True,
        tracking=True,
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
        domain="[('l10n_gr_edi_mark', '!=', False), ('state', '=', 'posted')]",
        compute='_compute_l10n_gr_edi_correlation_id',
        store=True,
    )
    l10n_gr_edi_payment_method = fields.Selection(
        selection=PAYMENT_METHOD_SELECTION,
        string='MyDATA Payment Method',
        default='1',
    )
    l10n_gr_edi_warnings = fields.Json(compute='_compute_l10n_gr_edi_warnings')
    l10n_gr_edi_need_correlated = fields.Boolean(compute='_compute_l10n_gr_edi_need_fields')
    l10n_gr_edi_need_payment_method = fields.Boolean(compute='_compute_l10n_gr_edi_need_fields')
    l10n_gr_edi_enable_send_invoices = fields.Boolean(compute='_compute_l10n_gr_edi_enable_send')
    l10n_gr_edi_enable_send_expense_classification = fields.Boolean(compute='_compute_l10n_gr_edi_enable_send')
    l10n_gr_edi_attachment_id = fields.Many2one(comodel_name='ir.attachment')

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

    @api.depends('country_code', 'state')
    def _compute_l10n_gr_edi_warnings(self):
        for move in self:
            # Warnings are only calculated when the move state is posted
            if move.country_code == 'GR' and move.state == 'posted':
                warnings = move._l10n_gr_edi_get_pre_error_dict()
                move.l10n_gr_edi_warnings = warnings
            else:
                move.l10n_gr_edi_warnings = False

    @api.depends('state', 'l10n_gr_edi_state')
    def _compute_l10n_gr_edi_enable_send(self):
        for move in self:
            common_requirements = all((
                move.country_code == 'GR',
                move.state == 'posted',
                move.l10n_gr_edi_state != 'move_sent',
            ))
            move.l10n_gr_edi_enable_send_invoices = all((
                common_requirements,
                move.move_type in ('out_invoice', 'out_refund'),
            ))
            move.l10n_gr_edi_enable_send_expense_classification = all((
                common_requirements,
                move.move_type in ('in_invoice', 'in_refund'),
                move.l10n_gr_edi_mark,
            ))

    ################################################################################
    # Dynamic Selection Field Computes
    ################################################################################

    @api.depends('move_type')
    def _compute_l10n_gr_edi_available_inv_type(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                move.l10n_gr_edi_available_inv_type = ','.join(INVOICE_TYPES_HAVE_INCOME)
            else:
                move.l10n_gr_edi_available_inv_type = ','.join(INVOICE_TYPES_HAVE_EXPENSE)

    @api.depends('fiscal_position_id', 'l10n_gr_edi_available_inv_type')
    def _compute_l10n_gr_edi_inv_type(self):
        for move in self:
            if move._origin.l10n_gr_edi_inv_type:
                # get the real current inv type, needed for calculating line's cls category & type
                move.l10n_gr_edi_inv_type = move._origin.l10n_gr_edi_inv_type
            elif move.move_type in ('out_refund', 'in_refund'):
                # inv_type specific for credit notes
                if move.l10n_gr_edi_mark:
                    # when possible, we must add the associate invoice/bill mark (id)
                    move.l10n_gr_edi_inv_type = '5.1'
                else:
                    move.l10n_gr_edi_inv_type = '5.2'
            else:
                inv_type = '1.1' if move.move_type == 'out_invoice' else '13.1'
                preferred_cls_ids = move.fiscal_position_id.l10n_gr_edi_preferred_classification_ids.filtered(
                    lambda p: p.l10n_gr_edi_inv_type in move.l10n_gr_edi_available_inv_type.split(','))
                if preferred_cls_ids:
                    inv_type = preferred_cls_ids[0].l10n_gr_edi_inv_type
                move.l10n_gr_edi_inv_type = inv_type

    @api.depends('l10n_gr_edi_inv_type')
    def _compute_l10n_gr_edi_need_fields(self):
        for move in self:
            move.l10n_gr_edi_need_correlated = move.l10n_gr_edi_inv_type in TYPES_WITH_CORRELATE_INVOICE
            move.l10n_gr_edi_need_payment_method = move.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_PAYMENT

    @api.depends('l10n_gr_edi_need_correlated')
    def _compute_l10n_gr_edi_correlation_id(self):
        for move in self:
            if move.l10n_gr_edi_need_correlated:
                move.l10n_gr_edi_correlation_id = move.l10n_gr_edi_correlation_id

                # automatically compute the correlated move id
                if move.move_type in ('out_refund', 'in_refund') and (correlated_move := self.env['account.move'].search([
                    ('company_id', '=', move.company_id.id),
                    ('l10n_gr_edi_mark', '=', move.l10n_gr_edi_mark),
                    ('move_type', '=', 'out_invoice' if move.move_type == 'out_refund' else 'in_invoice'),
                ], limit=1)):
                    move.l10n_gr_edi_correlation_id = correlated_move
            else:
                move.l10n_gr_edi_correlation_id = False

    ################################################################################
    # Greece Document Handler
    ################################################################################

    def _l10n_gr_edi_create_attachment_values(self, raw, res_model=None, res_id=None):
        """ Shorthand for creating the attachment_id values on the invoice's document """
        self.ensure_one()
        res_model = res_model or self._name
        res_id = res_id or self.id
        return {
            'name': f"mydata_{self.name.replace('/', '_')}.xml",
            'res_model': res_model,
            'res_id': res_id,
            'raw': raw,
            'type': 'binary',
            'mimetype': 'application/xml',
        }

    def _l10n_gr_edi_create_document_move_error(self, message, xml_content=''):
        self.ensure_one()
        document = self.env['l10n_gr_edi.document'].create({
            'move_id': self.id,
            'state': 'move_error',
            'message': message,
        })
        if xml_content:
            attachment_values = self._l10n_gr_edi_create_attachment_values(
                raw=xml_content,
                res_model=document._name,
                res_id=document.id,
            )
            document.attachment_id = self.env['ir.attachment'].sudo().create(attachment_values)
        return document

    def _l10n_gr_edi_create_document_move_sent(self, xml_content):
        self.ensure_one()
        document = self.env['l10n_gr_edi.document'].create({
            'move_id': self.id,
            'state': 'move_sent',
        })
        attachment = self.env['ir.attachment'].sudo().create(self._l10n_gr_edi_create_attachment_values(xml_content))
        document.attachment_id = self.l10n_gr_edi_attachment_id = attachment
        return document

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
    def _l10n_gr_edi_generate_xml_content(self, xml_template, xml_vals):
        xml_content = self.env['ir.qweb']._render(xml_template, xml_vals)
        xml_content = etree.tostring(cleanup_xml_node(xml_content), encoding='ISO-8859-7', standalone='yes')
        xml_content = xml_content.decode('iso8859_7')
        return xml_content

    @api.model
    def _l10n_gr_edi_create_move_xml_map(self, xml_vals):
        """ Creates and returns a dictionary mapping of `move_id` -> `xml_content` """
        move_xml_map = {}

        for invoice_vals in xml_vals['invoices']:
            single_xml_vals = {'invoices': [invoice_vals]}
            xml_content = self._l10n_gr_edi_generate_xml_content('l10n_gr_edi.send_invoice', single_xml_vals)
            move_xml_map[invoice_vals['__move__']] = xml_content

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
            elif move.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_COUNTERPART:  # not from Greece but require address
                party_vals.update({
                    'counterpart_postal_code': move.partner_id.zip,
                    'counterpart_city': move.partner_id.city.encode('utf-8'),
                })

        return party_vals

    @api.model
    def _l10n_gr_edi_get_payment_method_vals(self, move):
        payment_vals = {'payment_details': []}
        reconciled_lines = move.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

        for apr in reconciled_lines.matched_credit_ids:  # for out_invoice/refund payment
            payment_vals['payment_details'].append({
                'type': move.l10n_gr_edi_payment_method or '1',
                'amount': apr.debit_amount_currency,
            })
        for apr in reconciled_lines.matched_debit_ids:  # for in_invoice/refund payment
            payment_vals['payment_details'].append({
                'type': move.l10n_gr_edi_payment_method or '1',
                'amount': apr.credit_amount_currency,
            })
        if not payment_vals['payment_details'] and move.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_PAYMENT:
            # paymentMethods element is required, even if its amount is zero (no payment have been made yet)
            payment_vals['payment_details'].append({
                'type': move.l10n_gr_edi_payment_method or '1',
                'amount': 0,
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
                '__move__': move,  # will not be rendered; for creating {move_id -> move_xml} mapping
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
                '__move__': move,
                'mark': move.l10n_gr_edi_mark,
                'transaction_mode': '',  # Later, add a way to 'reject' received invoices
                'details': details,
            })

        xml_vals = self._l10n_gr_edi_cleanup_xml_vals(xml_vals)
        return xml_vals

    ################################################################################
    # Send Logics
    ################################################################################

    def _l10n_gr_edi_get_pre_error_dict(self):
        """
        Try to catch all possible errors before sending to MyDATA.
        Returns an error dictionary in the format of Actionable Error JSON.
        """
        self.ensure_one()
        move = self._origin  # make sure the validated move have all the latest data (to handle calling from compute methods)
        errors = {}
        error_action_company = {'action_text': _("View Company"), 'action': move.company_id._get_records_action(name=_("Company"))}
        error_action_partner = {'action_text': _("View Partner"), 'action': move.partner_id._get_records_action(name=_("Partner"))}

        if not move.company_id.l10n_gr_edi_aade_id or not move.company_id.l10n_gr_edi_aade_key:
            errors['l10n_gr_edi_company_no_cred'] = {
                'message': _("You need to set AADE ID and Key in the company settings."),
                **error_action_company,
            }
        if move.country_code != 'GR' and (not move.company_id.city or not move.company_id.zip):
            errors['l10n_gr_edi_company_no_zip_street'] = {
                'message': _("Missing city and/or ZIP code on company %s.", move.company_id.name),
                **error_action_company,
            }
        if not move.company_id.vat:
            errors['l10n_gr_edi_company_no_vat'] = {
                'message': _("Missing VAT on company %s.", move.company_id.name),
                **error_action_company,
            }
        if not move.l10n_gr_edi_inv_type:
            errors['l10n_gr_edi_no_inv_type'] = {
                'message': _("Missing MyDATA Invoice Type."),
            }
        if not move.partner_id:
            errors['l10n_gr_edi_no_partner'] = {
                'message': _("Partner must be filled to be able to send to MyDATA."),
            }
        if move.partner_id:
            if not move.partner_id.vat:
                errors['l10n_gr_edi_partner_no_vat'] = {
                    'message': _("Missing VAT on partner %s.", move.partner_id.name),
                    **error_action_partner,
                }
            if ((move.partner_id.country_code != 'GR' or move.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_COUNTERPART) and
                    (not move.partner_id.zip or not move.partner_id.city)):
                errors['l10n_gr_edi_partner_no_zip_street'] = {
                    'message': _("Missing city and/or ZIP code on partner %s.", move.partner_id.name),
                    **error_action_partner,
                }

        for line_no, line in enumerate(move.invoice_line_ids, start=1):
            if not line.l10n_gr_edi_cls_category and line.l10n_gr_edi_available_cls_category:
                errors[f'l10n_gr_edi_line_{line_no}_missing_cls_category'] = {
                    'message': _('Missing MyDATA classification category on line %s.', line_no),
                }
            if not line.l10n_gr_edi_cls_type \
                    and line.l10n_gr_edi_available_cls_type \
                    and (line.move_id.l10n_gr_edi_inv_type, line.l10n_gr_edi_cls_category) \
                    not in COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE:
                errors[f'l10n_gr_edi_line_{line_no}_missing_cls_type'] = {
                    'message': _('Missing MyDATA classification type on line %s.', line_no),
                }
            if len(line.tax_ids) > 1:
                errors[f'l10n_gr_edi_line_{line_no}_multi_tax'] = {
                    'message': _('MyDATA does not support multiple taxes on line %s.', line_no),
                }
            if not line.tax_ids and move.l10n_gr_edi_inv_type not in TYPES_WITH_VAT_CATEGORY_8:
                errors[f'l10n_gr_edi_line_{line_no}_missing_tax'] = {
                    'message': _('Missing tax on line %s.', line_no),
                }
            if len(line.tax_ids) == 1 and line.tax_ids.amount == 0 and not line.l10n_gr_edi_tax_exemption_category:
                errors[f'l10n_gr_edi_line_{line_no}_missing_tax_exempt'] = {
                    'message': _('Missing MyDATA Tax Exemption Category for line %s.', line_no),
                }
            if len(line.tax_ids) == 1 and line.tax_ids.amount not in VALID_TAX_AMOUNTS:
                errors[f'l10n_gr_edi_line_{line_no}_invalid_tax_amount'] = {
                    'message': _('Invalid tax amount for line %s. The valid values are %s.',
                                 line_no, ', '.join(str(tax) for tax in VALID_TAX_AMOUNTS)),
                }
        return errors

    def _l10n_gr_edi_get_pre_error_string(self):
        self.ensure_one()
        pre_error = self._l10n_gr_edi_get_pre_error_dict()
        error_messages = (error_val['message'] for error_val in pre_error.values())
        return '\n'.join(error_messages)

    @api.model
    def _l10n_gr_edi_handle_send_result(self, result, xml_vals):
        """ Handle the result object received from sending xml to myDATA.
            Create the related error/sent document with the necessary values. """
        move_xml_map = self._l10n_gr_edi_create_move_xml_map(xml_vals)
        move_ids = list(move_xml_map.keys())

        if 'error' in result:
            # If the request failed at this stage, it is probably caused by connection/credentials issues.
            # In such case, we don't need to attach the xml here as it won't be helpful for the user.
            for move in move_ids:
                move._l10n_gr_edi_create_document_move_error(result['error'])
            return

        for result_id, result_dict in result.items():
            move = move_ids[result_id]
            xml_content = move_xml_map[move]
            if 'error' in result_dict:
                # In this stage, the sending process has succeeded, and any error we receive is generated from the API.
                # Previous error(s) without attachments (generated from pre-compute) are now useless and can be unlinked.
                move.l10n_gr_edi_document_ids.filtered(lambda d: d.state == 'move_error' and not d.attachment_id).unlink()
                move._l10n_gr_edi_create_document_move_error(result_dict['error'], xml_content)
            else:
                move.l10n_gr_edi_mark = result_dict['l10n_gr_edi_mark']
                if result_dict.get('l10n_gr_edi_cls_mark'):
                    move.l10n_gr_edi_cls_mark = result_dict['l10n_gr_edi_cls_mark']
                move.l10n_gr_edi_document_ids.filtered(lambda d: d.state == 'move_error').unlink()
                move._l10n_gr_edi_create_document_move_sent(xml_content)

    def _l10n_gr_edi_send_invoices(self):
        """ Send batch of invoices SendInvoice XML to MyDATA. """
        xml_vals = self._l10n_gr_edi_get_invoices_xml_vals()
        xml_content = self._l10n_gr_edi_generate_xml_content('l10n_gr_edi.send_invoice', xml_vals)
        result = self.env['l10n_gr_edi.document']._mydata_send_invoices(company=self.company_id, xml_content=xml_content)
        self._l10n_gr_edi_handle_send_result(result, xml_vals)

    def _l10n_gr_edi_send_expense_classification(self):
        """ Send batch of invoices SendExpensesClassification XML to MyDATA. """
        xml_vals = self._l10n_gr_edi_get_expense_classification_xml_vals()
        xml_content = self._l10n_gr_edi_generate_xml_content('l10n_gr_edi.send_expense_classification', xml_vals)
        result = self.env['l10n_gr_edi.document']._mydata_send_expense_classification(company=self.company_id, xml_content=xml_content)
        self._l10n_gr_edi_handle_send_result(result, xml_vals)

    def _l10n_gr_edi_get_moves_to_send(self):
        """ This method pre-compute the errors in each of move inside `self` and returns the "good" move(s).
            If we only send one move (the most common scenario), any errors detected will be raised immediately.
            Otherwise, an error document will be created on each problematic move(s).
            The problematic move(s) will not be returned. """
        moves_to_send = self.env['account.move']
        for move in self:
            if errors := move._l10n_gr_edi_get_pre_error_string():
                if len(self) == 1:  # raise immediately when sending single move
                    raise UserError(errors)
                else:  # create error document when sending multiple moves
                    self._l10n_gr_edi_create_document_move_error(move.id, errors)
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

    def _l10n_gr_edi_try_send_batch(self):
        """ Only available for Vendor Bills. In case of invoices, user should use Send & Print instead. """
        if any(move.is_sale_document(include_receipts=True) for move in self):
            raise UserError(_("You should use Send & Print wizard for sending customer invoices to MyDATA."))
        if any(not move.l10n_gr_edi_enable_send_expense_classification for move in self):
            raise UserError(_("Some of the selected moves does not meet the requirements to be sent to MyDATA."))

        self.l10n_gr_edi_try_send_expense_classification()
