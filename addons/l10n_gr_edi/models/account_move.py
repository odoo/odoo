from lxml import etree
from urllib.parse import urlencode

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node
from odoo.tools.sql import column_exists, create_column

from odoo.addons.l10n_gr_edi.models.l10n_gr_edi_document import _make_mydata_request
from odoo.addons.l10n_gr_edi.models.preferred_classification import (
    CLASSIFICATION_CATEGORY_EXPENSE,
    COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE,
    INVOICE_TYPES_HAVE_EXPENSE,
    INVOICE_TYPES_HAVE_INCOME,
    INVOICE_TYPES_SELECTION,
    PAYMENT_METHOD_SELECTION,
    TYPES_WITH_CORRELATE_INVOICE,
    TYPES_WITH_FORBIDDEN_CLASSIFICATION,
    TYPES_WITH_FORBIDDEN_COUNTERPART,
    TYPES_WITH_FORBIDDEN_QUANTITY,
    TYPES_WITH_MANDATORY_COUNTERPART,
    TYPES_WITH_MANDATORY_PAYMENT,
    TYPES_WITH_VAT_CATEGORY_8,
    TYPES_WITH_VAT_EXEMPT,
    VALID_TAX_AMOUNTS,
    VALID_TAX_CATEGORY_MAP,
)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_gr_edi_mark = fields.Char(
        string='Mark',
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
    )
    l10n_gr_edi_cls_mark = fields.Char(
        string='Classification Mark',
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
    )
    l10n_gr_edi_document_ids = fields.One2many(
        comodel_name='l10n_gr_edi.document',
        inverse_name='move_id',
        copy=False,
        readonly=True,
    )
    l10n_gr_edi_state = fields.Selection(
        selection=[
            ('invoice_sent', 'Invoice sent'),
            ('bill_fetched', "Expense classification ready to send"),
            ('bill_sent', "Expense classification sent"),
        ],
        string='myDATA Status',
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
        tracking=True,
    )
    l10n_gr_edi_available_inv_type = fields.Char(compute='_compute_l10n_gr_edi_available_inv_type')
    l10n_gr_edi_correlation_id = fields.Many2one(
        comodel_name='account.move',
        string='Correlated Invoice',
    )
    l10n_gr_edi_inv_type = fields.Selection(
        selection=INVOICE_TYPES_SELECTION,
        string='myDATA Invoice Type',
        compute='_compute_l10n_gr_edi_inv_type',
        store=True,
        readonly=False,
    )
    l10n_gr_edi_payment_method = fields.Selection(
        selection=PAYMENT_METHOD_SELECTION,
        string='Payment Method',
        compute='_compute_l10n_gr_edi_payment_method',
        store=True,
    )
    l10n_gr_edi_alerts = fields.Json(compute='_compute_l10n_gr_edi_alerts')
    l10n_gr_edi_need_correlated = fields.Boolean(compute='_compute_l10n_gr_edi_need_fields')
    l10n_gr_edi_need_payment_method = fields.Boolean(compute='_compute_l10n_gr_edi_need_fields')
    l10n_gr_edi_enable_view_mydata = fields.Boolean(compute='_compute_l10n_gr_edi_enable_fields')
    l10n_gr_edi_enable_send_invoices = fields.Boolean(compute='_compute_l10n_gr_edi_enable_fields')
    l10n_gr_edi_enable_send_expense_classification = fields.Boolean(compute='_compute_l10n_gr_edi_enable_fields')
    l10n_gr_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute='_compute_from_l10n_gr_edi_document_ids',
        store=True,
    )

    def _auto_init(self):
        """
        Create all compute-stored fields here to avoid MemoryError when initializing on large databases.
        """
        for column_name, column_type in (
            ('l10n_gr_edi_mark', 'varchar'),
            ('l10n_gr_edi_cls_mark', 'varchar'),
            ('l10n_gr_edi_state', 'varchar'),
            ('l10n_gr_edi_inv_type', 'varchar'),
            ('l10n_gr_edi_payment_method', 'varchar'),
            ('l10n_gr_edi_attachment_id', 'int4'),
        ):
            if not column_exists(self.env.cr, 'account_move', column_name):
                create_column(self.env.cr, 'account_move', column_name, column_type)

        return super()._auto_init()

    ################################################################################
    # Standard Field Computes
    ################################################################################

    @api.depends('l10n_gr_edi_document_ids')
    def _compute_from_l10n_gr_edi_document_ids(self):
        self.l10n_gr_edi_state = False
        self.l10n_gr_edi_mark = False
        self.l10n_gr_edi_cls_mark = False
        self.l10n_gr_edi_attachment_id = False

        for move in self:
            for document in move.l10n_gr_edi_document_ids.sorted():
                if document.state in ('invoice_sent', 'bill_fetched', 'bill_sent'):
                    move.l10n_gr_edi_state = document.state
                    move.l10n_gr_edi_mark = document.mydata_mark
                    move.l10n_gr_edi_cls_mark = document.mydata_cls_mark
                    move.l10n_gr_edi_attachment_id = document.attachment_id
                    break

    @api.depends('l10n_gr_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        """ Prevent user from resetting the move to draft if it's already sent to myDATA """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_gr_edi_state in ('invoice_sent', 'bill_sent'):
                move.show_reset_to_draft_button = False

    @api.depends('country_code', 'state')
    def _compute_l10n_gr_edi_alerts(self):
        for move in self:
            # Warnings are only calculated when the move state is posted.
            # We use `._origin` to make sure the validated move have all the needed data for validation.
            if move._l10n_gr_edi_eligible_for_mydata():
                move.l10n_gr_edi_alerts = move._origin._l10n_gr_edi_get_pre_error_dict()
            else:
                move.l10n_gr_edi_alerts = False

    @api.depends('state', 'l10n_gr_edi_state')
    def _compute_l10n_gr_edi_enable_fields(self):
        for move in self:
            common_send_requirements = all((
                move._l10n_gr_edi_eligible_for_mydata(),
                move.l10n_gr_edi_state in (False, 'bill_fetched'),
            ))
            move.l10n_gr_edi_enable_view_mydata = all((
                move.country_code == 'GR',
                move.is_invoice(include_receipts=True),
            ))
            move.l10n_gr_edi_enable_send_invoices = all((
                common_send_requirements,
                move.is_sale_document(include_receipts=True),
            ))
            move.l10n_gr_edi_enable_send_expense_classification = all((
                common_send_requirements,
                move.is_purchase_document(include_receipts=True),
                move.l10n_gr_edi_mark,
            ))

    @api.depends('country_code')
    def _compute_l10n_gr_edi_payment_method(self):
        for move in self:
            if move.country_code == 'GR':
                move.l10n_gr_edi_payment_method = move.l10n_gr_edi_payment_method or '1'
            else:
                move.l10n_gr_edi_payment_method = False

    ################################################################################
    # Dynamic Selection Field Computes
    ################################################################################

    @api.depends('move_type')
    def _compute_l10n_gr_edi_available_inv_type(self):
        for move in self:
            if move.is_sale_document(include_receipts=True):
                move.l10n_gr_edi_available_inv_type = ','.join(INVOICE_TYPES_HAVE_INCOME)
            elif move.is_purchase_document(include_receipts=True):
                move.l10n_gr_edi_available_inv_type = ','.join(INVOICE_TYPES_HAVE_EXPENSE)
            else:  # move.move_type == 'entry'
                move.l10n_gr_edi_available_inv_type = False

    @api.depends('fiscal_position_id', 'l10n_gr_edi_available_inv_type')
    def _compute_l10n_gr_edi_inv_type(self):
        for move in self:
            if move.country_code == 'GR':
                if move.l10n_gr_edi_inv_type or move.move_type == 'entry':
                    # If we have previously calculated the inv_type, reuse it here.
                    # For entry moves, we want the inv_type to be False. (we don't send anything to myDATA on entry moves)
                    move.l10n_gr_edi_inv_type = move.l10n_gr_edi_inv_type
                elif move.move_type in ('out_refund', 'in_refund'):
                    # inv_type specific for credit notes
                    if move.l10n_gr_edi_correlation_id:
                        # when possible, we must add the associate invoice/bill mark (id)
                        move.l10n_gr_edi_inv_type = '5.1'
                    else:
                        move.l10n_gr_edi_inv_type = '5.2'
                else:  # move.move_type in ('out_invoice', 'in_invoice', 'out_receipt', 'in_receipt')
                    inv_type = '1.1' if move.move_type == 'out_invoice' else '13.1'
                    preferred_clss = move.fiscal_position_id.l10n_gr_edi_preferred_classification_ids.filtered(
                        lambda p: p.l10n_gr_edi_inv_type in (move.l10n_gr_edi_available_inv_type or "").split(','))
                    if preferred_clss:
                        inv_type = preferred_clss[0].l10n_gr_edi_inv_type
                    move.l10n_gr_edi_inv_type = inv_type
            else:
                move.l10n_gr_edi_inv_type = False

    @api.depends('l10n_gr_edi_inv_type')
    def _compute_l10n_gr_edi_need_fields(self):
        for move in self:
            move.l10n_gr_edi_need_correlated = all((
                move.l10n_gr_edi_inv_type in TYPES_WITH_CORRELATE_INVOICE,
                move.is_sale_document(include_receipts=True),
            ))
            move.l10n_gr_edi_need_payment_method = move.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_PAYMENT

    ################################################################################
    # Greece Document Helpers
    ################################################################################

    def _l10n_gr_edi_create_error_document(self, values: dict):
        """
        Creates ``l10n_gr_edi.document`` of state ``invoice_error`` or ``bill_error``.
        :param values: dictionary in the format of: {'error': <str>, 'xml_content': <optional/str>}
        """
        self.ensure_one()
        document = self.env['l10n_gr_edi.document'].create({
            'move_id': self.id,
            'state': 'invoice_error' if self.is_sale_document(include_receipts=True) else 'bill_error',
            'message': values['error'],
        })
        if xml_content := values.get('xml_content'):
            document.attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"mydata_{self.name.replace('/', '_')}.xml",
                'res_model': document._name,
                'res_id': document.id,
                'raw': xml_content,
                'type': 'binary',
                'mimetype': 'application/xml',
            })
        return document

    def _l10n_gr_edi_create_sent_document(self, values: dict):
        """
        Creates ``l10n_gr_edi.document`` of state ``invoice_sent`` or ``bill_sent``.
        :param values: dictionary in the format of:
        {
            'mydata_mark': <str>,
            'mydata_cls_mark': <optional/str>,
            'mydata_url': <str>,
            'xml_content': <str>,
        }
        """
        self.ensure_one()
        document = self.env['l10n_gr_edi.document'].create({
            'move_id': self.id,
            'state': 'invoice_sent' if self.is_sale_document(include_receipts=True) else 'bill_sent',
            'mydata_mark': values['mydata_mark'],
            'mydata_cls_mark': values.get('mydata_cls_mark'),
            'mydata_url': values['mydata_url'],
        })
        document.attachment_id = self.env['ir.attachment'].sudo().create({
            'name': f"mydata_{self.name.replace('/', '_')}.xml",
            'res_model': self._name,
            'res_id': self.id,
            'raw': values['xml_content'],
            'type': 'binary',
            'mimetype': 'application/xml',
        })
        return document

    ################################################################################
    # Helpers
    ################################################################################

    @api.model
    def _l10n_gr_edi_generate_xml_content(self, xml_template, xml_vals):
        xml_content = self.env['ir.qweb']._render(xml_template, xml_vals)
        return etree.tostring(element_or_tree=cleanup_xml_node(xml_content), encoding='ISO-8859-7', standalone='yes')

    def _l10n_gr_edi_eligible_for_mydata(self):
        """Shorthand for getting the eligibility of the current move to send to myDATA."""
        self.ensure_one()
        return all((
            self.country_code == 'GR',
            self.state == 'posted',
        ))

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.l10n_gr_edi_state == 'invoice_sent':
            return 'l10n_gr_edi.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_gr_edi_get_extra_invoice_report_values(self):
        """Get the values used to render the invoice PDF."""
        self.ensure_one()
        document = self.l10n_gr_edi_document_ids.sorted()[:1]

        if document.state in ('invoice_sent', 'bill_sent'):
            barcode_params = urlencode({
                'barcode_type': 'QR',
                'quiet': 0,
                'value': document.mydata_url,
                'width': 180,
                'height': 180,
            })
            return {
                'barcode_src': f'/report/barcode/?{barcode_params}',
                'mydata_mark': document.mydata_mark,
                'mydata_cls_mark': document.mydata_cls_mark,
            }
        else:
            return {}

    ################################################################################
    # Prepare XML Values
    ################################################################################

    def _l10n_gr_edi_add_address_vals(self, values):
        """
        Adds all the address values needed for the ``invoice_vals`` dictionary.
        The only guaranteed keys in to add in the dictionary is the issuer's VAT, country code, and branch number.
        Everything else is only displayed on some specific case/configuration.
        The appended dictionary will have the following additional keys:
        {
            'issuer_vat_number': <str>,
            'issuer_country': <str>,
            'issuer_branch': <int>,
            'issuer_name': <str | None>,
            'issuer_postal_code': <str | None>,
            'issuer_city': <str | None>,
            'counterpart_vat': <str | None>,
            'counterpart_country': <str | None>,
            'counterpart_branch': <int | None>,
            'counterpart_name': <str | None>,
            'counterpart_postal_code': <str | None>,
            'counterpart_city': <str | None>,
            'counterpart_postal_code': <str | None>,
            'counterpart_city': <str | None>,
        }
        :param dict values: dictionary where the address values will be added
        :rtype: dict[str, str|int]
        """
        self.ensure_one()
        issuer_not_from_greece = self.company_id.country_code != 'GR'
        inv_type_allows_counterpart = self.l10n_gr_edi_inv_type not in TYPES_WITH_FORBIDDEN_COUNTERPART
        partner_not_from_greece = self.partner_id.country_code != 'GR'
        inv_type_require_counterpart = self.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_COUNTERPART

        conditional_address_keys = ('issuer_name', 'issuer_postal_code', 'issuer_city', 'counterpart_vat', 'counterpart_country',
                                    'counterpart_branch', 'counterpart_name', 'counterpart_postal_code', 'counterpart_city')
        values.update({
            'issuer_vat_number': self.company_id.vat.replace('EL', '').replace('GR', ''),
            'issuer_country': self.company_id.country_code,
            'issuer_branch': self.company_id.l10n_gr_edi_branch_number or 0,
            **dict.fromkeys(conditional_address_keys),
        })

        if issuer_not_from_greece:
            values.update({
                'issuer_name': self.company_id.name.encode('ISO-8859-7'),
                'issuer_postal_code': self.company_id.zip,
                'issuer_city': (self.company_id.city or "").encode('ISO-8859-7') or None,
            })

        if inv_type_allows_counterpart:
            values.update({
                'counterpart_vat': self.commercial_partner_id.vat.replace('EL', '').replace('GR', ''),
                'counterpart_country': self.commercial_partner_id.country_code,
                'counterpart_branch': (self.commercial_partner_id.l10n_gr_edi_branch_number or 0),
            })
            if partner_not_from_greece:
                values['counterpart_name'] = self.commercial_partner_id.name.encode('ISO-8859-7')

        if inv_type_require_counterpart or (inv_type_allows_counterpart and partner_not_from_greece):
            values.update({
                'counterpart_postal_code': self.commercial_partner_id.zip,
                'counterpart_city': (self.commercial_partner_id.city or "").encode('ISO-8859-7') or None,
            })

    def _l10n_gr_edi_add_payment_method_vals(self, values):
        """
        Adds payment values needed for the ``invoice_vals`` dictionary.
        The appended dictionary will have the following additional key:
        { 'payment_details': [ { 'type': <str>, 'amount': <float> }, ... ] }
        :param dict values:
        :rtype: dict[str, list[dict]]
        """
        self.ensure_one()
        values.update({'payment_details': []})
        payment_terms = self.line_ids.filtered(lambda line: line.display_type == 'payment_term')

        for match_field, amount_field in (('debit', 'credit'), ('credit', 'debit')):
            for apr in payment_terms[f'matched_{match_field}_ids']:
                values['payment_details'].append({
                    'type': self.l10n_gr_edi_payment_method or '1',
                    'amount': apr[f'{amount_field}_amount_currency'],
                })

        if not values['payment_details'] and self.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_PAYMENT:
            # paymentMethods element is required, even if its amount is zero (no payment have been made yet)
            values['payment_details'].append({
                'type': self.l10n_gr_edi_payment_method or '1',
                'amount': 0,
            })

    @api.model
    def _l10n_gr_edi_common_base_line_details_values(self, base_line):
        """
        Returns additional income/expense classification items ("icls"/"ecls") if needed for the detail values.
        The returned format is: {'ecls': [ {'category': <str>, 'type': <str>, 'amount': <float>}, ... ], 'icls': <same_as_ecls> }
        :param dict base_line: dictionary obtained from the tax computation helper methods; such as `_get_rounded_base_and_tax_lines`.
        :rtype: dict[str, list[dict]]
        """
        line = base_line['record']
        net_amount = base_line['tax_details']['raw_total_excluded']
        cls_vals = {'ecls': [], 'icls': []}

        if line.l10n_gr_edi_cls_category:
            cls_vals_list = cls_vals['ecls'] if line.l10n_gr_edi_cls_category in CLASSIFICATION_CATEGORY_EXPENSE else cls_vals['icls']
            cls_type = line.l10n_gr_edi_cls_type or ''
            if len(cls_type) > 0 and cls_type[0] == 'X':  # handle duplicate E3 type on inv type 17.5
                cls_type = cls_type[1:]

            cls_vals_list.append({
                'category': line.l10n_gr_edi_cls_category,
                'type': cls_type,
                'amount': net_amount,
            })
            if line.l10n_gr_edi_cls_vat:
                cls_vals_list.append({
                    'category': '',
                    'type': line.l10n_gr_edi_cls_vat,
                    'amount': net_amount,
                })

        return cls_vals

    @api.model
    def _l10n_gr_edi_add_sum_classification_vals(self, values):
        """
        Aggregates all amounts from the common categories and types of the list vals from the ``details`` key,
        and then add them to the `values` dictionary parameter.
        [!WARNING!] The `values` parameter **must** have the `details` key.
        let ``XCLSList`` be a list with format of:
        [
            {'category': <str>, 'type': <str>, 'amount': <float>},
            ...,
        ]
        All in all, a subset of the `values` parameter should follow the following type formats:
        {
            'details': {
                'icls': XCLSList,
                'ecls': XCLSList,
            }
        }
        The `values` dictionary will then be appended with the following keys:
        {
            'summary_icls': XCLSList,
            'summary_ecls': XCLSList,
        }
        :param dict values: the dictionary where the sum classification values will be added.
        :rtype: dict[str, list[dict]]
        """
        cls_vals_type = dict[tuple[str, str], float]
        icls_vals: cls_vals_type = {}
        ecls_vals: cls_vals_type = {}

        for detail in values['details']:
            icls_list, ecls_list = detail['icls'], detail['ecls']
            for icls in icls_list:
                category_type = (icls['category'], icls['type'])
                icls_vals.setdefault(category_type, 0)
                icls_vals[category_type] += icls['amount']
            for ecls in ecls_list:
                category_type = (ecls['category'], ecls['type'])
                ecls_vals.setdefault(category_type, 0)
                ecls_vals[category_type] += ecls['amount']

        for summary_key, cls_vals in (
            ('summary_icls', icls_vals),
            ('summary_ecls', ecls_vals),
        ):
            values[summary_key] = [
                {
                    'category': category,
                    'type': cls_type,
                    'amount': total_amount,
                }
                for (category, cls_type), total_amount in cls_vals.items()
            ]

    def _l10n_gr_edi_get_invoices_xml_vals(self):
        """
        Generates a dictionary containing the values needed for rendering ``l10n_gr_edi.mydata_invoice`` XML.
        :return: dict
        """
        xml_vals = {'invoice_values_list': []}

        for move in self.sorted(key='id'):
            details = []
            base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()

            for line_no, base_line in enumerate(base_lines, start=1):
                line = base_line['record']
                vat_category = 8
                vat_exemption_category = ''
                if line.tax_ids and move.l10n_gr_edi_inv_type not in TYPES_WITH_VAT_EXEMPT:
                    tax = base_line['tax_details']['taxes_data'][0]['tax']  # here, `tax` is guaranteed to be a single `account.tax` record
                    vat_category = VALID_TAX_CATEGORY_MAP[int(tax.amount)]
                if vat_category == 7 and move.l10n_gr_edi_inv_type in TYPES_WITH_VAT_CATEGORY_8:
                    vat_category = 8
                if vat_category == 7:  # Need vat exemption category
                    vat_exemption_category = line.l10n_gr_edi_tax_exemption_category

                details.append({
                    'line_number': line_no,
                    'quantity': line.quantity if move.l10n_gr_edi_inv_type not in TYPES_WITH_FORBIDDEN_QUANTITY else '',
                    'detail_type': line.l10n_gr_edi_detail_type or '',
                    'net_value': base_line['tax_details']['raw_total_excluded'],
                    'vat_amount': sum(tax_data['tax_amount'] for tax_data in base_line['tax_details']['taxes_data']),
                    'vat_category': vat_category,
                    'vat_exemption_category': vat_exemption_category,
                    **self._l10n_gr_edi_common_base_line_details_values(base_line),
                })

            invoice_values = {
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
            }
            move._l10n_gr_edi_add_address_vals(invoice_values)
            move._l10n_gr_edi_add_payment_method_vals(invoice_values)
            self._l10n_gr_edi_add_sum_classification_vals(invoice_values)
            xml_vals['invoice_values_list'].append(invoice_values)

        return xml_vals

    def _l10n_gr_edi_get_expense_classification_xml_vals(self):
        """
        Generates a dictionary containing the values needed for rendering ``l10n_gr_edi.mydata_expense_classification`` XML.
        :return: dict
        """
        xml_vals = {'invoice_values_list': []}

        for move in self:
            details = []
            base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()

            for line_no, base_line in enumerate(base_lines, start=1):
                details.append({
                    'line_number': line_no,
                    **self._l10n_gr_edi_common_base_line_details_values(base_line),
                })

            xml_vals['invoice_values_list'].append({
                '__move__': move,
                'mark': move.l10n_gr_edi_mark,
                'transaction_mode': '',  # Later, add a way to 'reject' received invoices
                'details': details,
            })

        return xml_vals

    ################################################################################
    # Send Logics
    ################################################################################

    def _l10n_gr_edi_get_pre_error_dict(self):
        """
        Try to catch all possible errors before sending to myDATA.
        Returns an error dictionary in the format of Actionable Error JSON.
        """
        self.ensure_one()
        errors = {}
        error_action_company = {'action_text': _("View Company"), 'action': self.company_id._get_records_action(name=_("Company"))}
        error_action_partner = {'action_text': _("View Partner"), 'action': self.commercial_partner_id._get_records_action(name=_("Partner"))}
        error_action_gr_settings = {
            'action_text': _("View Settings"),
            'action': {
                'name': _("Settings"),
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': '/odoo/settings#l10n_gr_edi_aade_settings',
            },
        }

        if self.state != 'posted':
            errors['l10n_gr_edi_move_not_posted'] = {
                'message': _("You can only send to myDATA from a posted invoice."),
            }
        if not self.company_id.l10n_gr_edi_aade_id or not self.company_id.l10n_gr_edi_aade_key:
            errors['l10n_gr_edi_company_no_cred'] = {
                'message': _("You need to set AADE ID and Key in the company settings."),
                **error_action_gr_settings,
            }
        if self.company_id.country_code != 'GR' and (not self.company_id.city or not self.company_id.zip):
            errors['l10n_gr_edi_company_no_zip_street'] = {
                'message': _("Missing city and/or ZIP code on company %s.", self.company_id.name),
                **error_action_company,
            }
        if not self.company_id.vat:
            errors['l10n_gr_edi_company_no_vat'] = {
                'message': _("Missing VAT on company %s.", self.company_id.name),
                **error_action_company,
            }
        if not self.l10n_gr_edi_inv_type:
            errors['l10n_gr_edi_no_inv_type'] = {
                'message': _("Missing myDATA Invoice Type."),
            }
        if not self.commercial_partner_id:
            errors['l10n_gr_edi_no_partner'] = {
                'message': _("Partner must be filled to be able to send to myDATA."),
            }
        if self.commercial_partner_id:
            if not self.commercial_partner_id.vat:
                errors['l10n_gr_edi_partner_no_vat'] = {
                    'message': _("Missing VAT on partner %s.", self.commercial_partner_id.name),
                    **error_action_partner,
                }
            if ((self.commercial_partner_id.country_code != 'GR' or self.l10n_gr_edi_inv_type in TYPES_WITH_MANDATORY_COUNTERPART) and
                    (not self.commercial_partner_id.zip or not self.commercial_partner_id.city)):
                errors['l10n_gr_edi_partner_no_zip_street'] = {
                    'message': _("Missing city and/or ZIP code on partner %s.", self.commercial_partner_id.name),
                    **error_action_partner,
                }

        move_disallow_classification = self.is_purchase_document(include_receipts=True) and self.l10n_gr_edi_inv_type in TYPES_WITH_FORBIDDEN_CLASSIFICATION

        for line_no, line in enumerate(self.invoice_line_ids, start=1):
            if line.display_type in ('line_section', 'line_subsection', 'line_note'):
                continue
            if move_disallow_classification and line.l10n_gr_edi_cls_category:
                errors[f'l10n_gr_edi_{line_no}_forbidden_classification'] = {
                    'message': _('myDATA classification is not allowed on line %s.', line_no),
                }
            if not line.l10n_gr_edi_cls_category and line.l10n_gr_edi_available_cls_category and not move_disallow_classification:
                errors[f'l10n_gr_edi_line_{line_no}_missing_cls_category'] = {
                    'message': _('Missing myDATA classification category on line %s.', line_no),
                }
            if not line.l10n_gr_edi_cls_type \
                    and line.l10n_gr_edi_available_cls_type \
                    and (line.move_id.l10n_gr_edi_inv_type, line.l10n_gr_edi_cls_category) \
                    not in COMBINATIONS_WITH_POSSIBLE_EMPTY_TYPE:
                errors[f'l10n_gr_edi_line_{line_no}_missing_cls_type'] = {
                    'message': _('Missing myDATA classification type on line %s.', line_no),
                }
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            if len(taxes) > 1:
                errors[f'l10n_gr_edi_line_{line_no}_multi_tax'] = {
                    'message': _('myDATA does not support multiple taxes on line %s.', line_no),
                }
            if not taxes and self.l10n_gr_edi_inv_type not in TYPES_WITH_VAT_CATEGORY_8:
                errors[f'l10n_gr_edi_line_{line_no}_missing_tax'] = {
                    'message': _('Missing tax on line %s.', line_no),
                }
            if len(taxes) == 1 and taxes.amount == 0 and not line.l10n_gr_edi_tax_exemption_category:
                errors[f'l10n_gr_edi_line_{line_no}_missing_tax_exempt'] = {
                    'message': _('Missing myDATA Tax Exemption Category for line %s.', line_no),
                }
            if len(taxes) == 1 and taxes.amount not in VALID_TAX_AMOUNTS:
                errors[f'l10n_gr_edi_line_{line_no}_invalid_tax_amount'] = {
                    'message': _('Invalid tax amount for line %(line_no)s. The valid values are %(valid_values)s.',
                                 line_no=line_no,
                                 valid_values=', '.join(str(tax) for tax in VALID_TAX_AMOUNTS)),
                }
        return errors

    def _l10n_gr_edi_get_pre_error_string(self):
        self.ensure_one()
        pre_error = self._l10n_gr_edi_get_pre_error_dict()
        error_messages = (error_val['message'] for error_val in pre_error.values())
        return '\n'.join(error_messages)

    @api.model
    def _l10n_gr_edi_handle_send_result(self, result, xml_vals):
        """
        Handle the result object received from sending xml to myDATA.
        Create the related error/sent document with the necessary values.
        """
        move_xml_map = {}  # Dictionary mapping of ``move_id`` -> ``xml_content``.
        for invoice_vals in xml_vals['invoice_values_list']:
            single_xml_vals = {'invoice_values_list': [invoice_vals]}
            move = invoice_vals['__move__']
            xml_template = 'l10n_gr_edi.mydata_invoice' if move.is_sale_document(include_receipts=True) else 'l10n_gr_edi.mydata_expense_classification'
            xml_content = self._l10n_gr_edi_generate_xml_content(xml_template, single_xml_vals)
            move_xml_map[move] = xml_content

        move_ids = list(move_xml_map.keys())

        if 'error' in result:
            # If the request failed at this stage, it is probably caused by connection/credentials issues.
            # In such case, we don't need to attach the xml here as it won't be helpful for the user.
            for move in move_ids:
                move._l10n_gr_edi_create_error_document(result)
        else:
            for result_id, result_dict in result.items():
                move = move_ids[result_id]
                xml_content = move_xml_map[move]
                document_values = {**result_dict, 'xml_content': xml_content}
                # Delete previous error documents
                move.l10n_gr_edi_document_ids.filtered(lambda d: d.state in ('invoice_error', 'bill_error')).unlink()
                if 'error' in result_dict:
                    # In this stage, the sending process has succeeded, and any error we receive is generated from the myDATA API.
                    # Previous error(s) without attachments (generated from pre-compute) are now useless and can be unlinked.
                    move._l10n_gr_edi_create_error_document(document_values)
                else:
                    move._l10n_gr_edi_create_sent_document(document_values)

        if self._can_commit():
            self.env.cr.commit()

    def _l10n_gr_edi_send_invoices(self):
        """ Send batches of invoice SendInvoice XML to myDATA. """
        for company, invoices in self.grouped('company_id').items():
            xml_vals = invoices._l10n_gr_edi_get_invoices_xml_vals()
            xml_content = invoices._l10n_gr_edi_generate_xml_content('l10n_gr_edi.mydata_invoice', xml_vals)
            result = _make_mydata_request(company=company, endpoint='SendInvoices', xml_content=xml_content)
            self._l10n_gr_edi_handle_send_result(result, xml_vals)

    def _l10n_gr_edi_send_expense_classification(self):
        """ Send batches of bill SendExpensesClassification XML to myDATA. """
        for company, bills in self.grouped('company_id').items():
            xml_vals = bills._l10n_gr_edi_get_expense_classification_xml_vals()
            xml_content = bills._l10n_gr_edi_generate_xml_content('l10n_gr_edi.mydata_expense_classification', xml_vals)
            result = _make_mydata_request(company=company, endpoint='SendExpensesClassification', xml_content=xml_content)
            self._l10n_gr_edi_handle_send_result(result, xml_vals)

    def l10n_gr_edi_try_send_invoices(self):
        moves_to_send = self.env['account.move']
        for move in self:
            if error := move._l10n_gr_edi_get_pre_error_string():
                move._l10n_gr_edi_create_error_document({'error': error})
            else:
                moves_to_send |= move

        if moves_to_send:
            self.env['res.company']._with_locked_records(moves_to_send)
            moves_to_send._l10n_gr_edi_send_invoices()

    def l10n_gr_edi_try_send_expense_classification(self):
        moves_to_send = self.env['account.move']
        for move in self:
            if error_message := move._l10n_gr_edi_get_pre_error_string():
                move._l10n_gr_edi_create_error_document({'error': error_message})

                # Simulate the error handling behavior on invoice's send and print wizard.
                # If we're only sending one bill, raise the warning error immediately.
                if len(self) == 1 and self._can_commit():
                    self.env.cr.commit()
                    raise UserError(error_message)
            else:
                moves_to_send |= move

        if moves_to_send:
            moves_to_send._l10n_gr_edi_send_expense_classification()
            if len(self) == 1 and (error_message := self.l10n_gr_edi_document_ids.sorted()[0].message):
                raise UserError(error_message)

    def _l10n_gr_edi_try_send_batch(self):
        """ Only available for Vendor Bills. In case of invoices, user should use Send & Print instead. """
        if any(move.is_sale_document(include_receipts=True) for move in self):
            raise UserError(_("You should use Send & Print wizard for sending customer invoices to myDATA."))
        if any(not move.l10n_gr_edi_enable_send_expense_classification for move in self):
            raise UserError(_("Some of the selected moves does not meet the requirements to be sent to myDATA."))

        self.l10n_gr_edi_try_send_expense_classification()
