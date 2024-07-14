# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt, Command
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError
from odoo.tools import float_compare, mute_logger
from odoo.tools.misc import clean_context, formatLang
from difflib import SequenceMatcher
import logging
import re
import json

_logger = logging.getLogger(__name__)

PARTNER_AUTOCOMPLETE_ENDPOINT = 'https://partner-autocomplete.odoo.com'
OCR_VERSION = 122


class AccountInvoiceExtractionWords(models.Model):
    _name = "account.invoice_extract.words"
    _description = "Extracted words from invoice scan"

    invoice_id = fields.Many2one("account.move", required=True, ondelete='cascade', index=True, string="Invoice")
    field = fields.Char()

    ocr_selected = fields.Boolean()
    user_selected = fields.Boolean()
    word_text = fields.Char()
    word_page = fields.Integer()
    word_box_midX = fields.Float()
    word_box_midY = fields.Float()
    word_box_width = fields.Float()
    word_box_height = fields.Float()
    word_box_angle = fields.Float()


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['extract.mixin', 'account.move']

    @api.depends('state')
    def _compute_is_in_extractable_state(self):
        for record in self:
            record.is_in_extractable_state = record.state == 'draft' and record.is_invoice()

    @api.depends(
        'state',
        'extract_state',
        'move_type',
        'company_id.extract_in_invoice_digitalization_mode',
        'company_id.extract_out_invoice_digitalization_mode',
    )
    def _compute_show_banners(self):
        for record in self:
            record.extract_can_show_banners = (
                record.state == 'draft' and
                (
                    (record.is_purchase_document() and record.company_id.extract_in_invoice_digitalization_mode != 'no_send') or
                    (record.is_sale_document() and record.company_id.extract_out_invoice_digitalization_mode != 'no_send')
                )
            )

    extract_word_ids = fields.One2many("account.invoice_extract.words", inverse_name="invoice_id", copy=False)
    extract_attachment_id = fields.Many2one('ir.attachment', readonly=True, ondelete='set null', copy=False, index='btree_not_null')
    extract_can_show_banners = fields.Boolean("Can show the ocr banners", compute=_compute_show_banners)

    extract_detected_layout = fields.Integer("Extract Detected Layout Id", readonly=True)
    extract_partner_name = fields.Char("Extract Detected Partner Name", readonly=True)

    def action_reload_ai_data(self):
        try:
            with self._get_edi_creation() as move_form:
                # The OCR doesn't overwrite the fields, so it's necessary to reset them
                move_form.partner_id = False
                move_form.invoice_date = False
                move_form.invoice_payment_term_id = False
                move_form.invoice_date_due = False

                if move_form.is_purchase_document():
                    move_form.ref = False
                elif move_form.is_sale_document() and move_form.quick_edit_mode:
                    move_form.name = False

                move_form.payment_reference = False
                move_form.currency_id = move_form.company_currency_id
                move_form.invoice_line_ids = [Command.clear()]
            self._check_ocr_status(force_write=True)
        except Exception as e:
            _logger.warning("Error while reloading AI data on account.move %d: %s", self.id, e)
            raise AccessError(_lt("Couldn't reload AI data."))

    @api.model
    def _contact_iap_extract(self, pathinfo, params):
        params['version'] = OCR_VERSION
        params['account_token'] = self._get_iap_account().account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('iap_extract_endpoint', 'https://extract.api.odoo.com')
        return iap_tools.iap_jsonrpc(endpoint + '/api/extract/invoice/2/' + pathinfo, params=params)

    @api.model
    def _contact_iap_partner_autocomplete(self, local_endpoint, params):
        return iap_tools.iap_jsonrpc(PARTNER_AUTOCOMPLETE_ENDPOINT + local_endpoint, params=params)

    def _check_digitalization_mode(self, company, document_type, mode):
        if document_type in self.get_purchase_types():
            return company.extract_in_invoice_digitalization_mode == mode
        elif document_type in self.get_sale_types():
            return company.extract_out_invoice_digitalization_mode == mode

    def _needs_auto_extract(self, new_document=False, file_type=''):
        """ Returns `True` if the document should be automatically sent to the extraction server"""
        self.ensure_one()

        # Check that the document meets the basic conditions for auto extraction
        if (
            self.extract_state != "no_extract_requested"
            or not self._check_digitalization_mode(self.company_id, self.move_type, 'auto_send')
            or not self.is_in_extractable_state
        ):
            return False

        if self._context.get('from_alias'):
            # If the document comes from the email alias, check that the file format is compatible with the journal setting
            if not file_type and self.message_main_attachment_id:
                file_type = self.message_main_attachment_id.mimetype.split('/')[1]
            return (
                not self.journal_id.alias_auto_extract_pdfs_only
                or file_type == 'pdf'
            )
        elif new_document:
            # New documents are always auto extracted
            return True

        # If it's an existing document to which an attachment is added, only auto extract it for purchase documents
        return self.is_purchase_document()

    def _get_ocr_module_name(self):
        return 'account_invoice_extract'

    def _get_ocr_option_can_extract(self):
        self.ensure_one()
        return not self._check_digitalization_mode(self.company_id, self.move_type, 'no_send')

    def _get_validation_domain(self):
        base_domain = super()._get_validation_domain()
        return base_domain + [('state', '=', 'posted')]

    def _get_validation_fields(self):
        return [
            'total', 'subtotal', 'total_tax_amount', 'date', 'due_date', 'invoice_id', 'partner',
            'VAT_Number', 'currency', 'payment_ref', 'iban', 'SWIFT_code', 'merged_lines', 'invoice_lines',
        ]

    def _get_user_error_invalid_state_message(self):
        return _("You cannot send a expense that is not in draft state!")

    def _upload_to_extract_success_callback(self):
        super()._upload_to_extract_success_callback()
        self.extract_attachment_id = self.message_main_attachment_id

    def is_indian_taxes(self):
        l10n_in = self.env['ir.module.module'].search([('name', '=', 'l10n_in')])
        return self.company_id.country_id.code == "IN" and l10n_in and l10n_in.state == 'installed'

    def _get_user_infos(self):
        user_infos = super()._get_user_infos()
        user_infos.update({
            'user_company_VAT': self.company_id.vat,
            'user_company_name': self.company_id.name,
            'user_company_country_code': self.company_id.country_id.code,
            'perspective': 'supplier' if self.is_sale_document() else 'client',
        })
        return user_infos

    def _upload_to_extract(self):
        """ Call parent method _upload_to_extract only if self is an invoice. """
        self.ensure_one()
        if self.is_invoice():
            super()._upload_to_extract()

    def _get_validation(self, field):
        """
        return the text or box corresponding to the choice of the user.
        If the user selected a box on the document, we return this box,
        but if he entered the text of the field manually, we return only the text, as we
        don't know which box is the right one (if it exists)
        """
        text_to_send = {}
        if field == "total":
            text_to_send["content"] = self.amount_total
        elif field == "subtotal":
            text_to_send["content"] = self.amount_untaxed
        elif field == "total_tax_amount":
            text_to_send["content"] = self.amount_tax
        elif field == "date":
            text_to_send["content"] = str(self.invoice_date) if self.invoice_date else False
        elif field == "due_date":
            text_to_send["content"] = str(self.invoice_date_due) if self.invoice_date_due else False
        elif field == "invoice_id":
            if self.is_purchase_document():
                text_to_send["content"] = self.ref
            else:
                text_to_send["content"] = self.name
        elif field == "partner":
            text_to_send["content"] = self.partner_id.name
        elif field == "VAT_Number":
            text_to_send["content"] = self.partner_id.vat
        elif field == "currency":
            text_to_send["content"] = self.currency_id.name
        elif field == "payment_ref":
            text_to_send["content"] = self.payment_reference
        elif field == "iban":
            text_to_send["content"] = self.partner_bank_id.acc_number if self.partner_bank_id else False
        elif field == "SWIFT_code":
            text_to_send["content"] = self.partner_bank_id.bank_bic if self.partner_bank_id else False
        elif field == 'merged_lines':
            return self.env.company.extract_single_line_per_tax
        elif field == "invoice_lines":
            text_to_send = {'lines': []}
            for il in self.invoice_line_ids:
                line = {
                    "description": il.name,
                    "quantity": il.quantity,
                    "unit_price": il.price_unit,
                    "product": il.product_id.id,
                    "taxes_amount": round(il.price_total - il.price_subtotal, 2),
                    "taxes": [{
                        'amount': tax.amount,
                        'type': tax.amount_type,
                        'price_include': tax.price_include} for tax in il.tax_ids],
                    "subtotal": il.price_subtotal,
                    "total": il.price_total
                }
                text_to_send['lines'].append(line)
            if self.is_indian_taxes():
                lines = text_to_send['lines']
                for index, line in enumerate(text_to_send['lines']):
                    for tax in line['taxes']:
                        taxes = []
                        if tax['type'] == 'group':
                            taxes.extend([{
                                'amount': tax['amount'] / 2,
                                'type': 'percent',
                                'price_include': tax['price_include']
                            } for _ in range(2)])
                        else:
                            taxes.append(tax)
                        lines[index]['taxes'] = taxes
                text_to_send['lines'] = lines
        else:
            return None

        user_selected_box = self.env['account.invoice_extract.words'].search([
            ('invoice_id', '=', self.id),
            ('field', '=', field),
            ('user_selected', '=', True),
            ('ocr_selected', '=', False),
        ])
        if user_selected_box and user_selected_box.word_text == text_to_send['content']:
            text_to_send['box'] = [
                user_selected_box.word_text,
                user_selected_box.word_page,
                user_selected_box.word_box_midX,
                user_selected_box.word_box_midY,
                user_selected_box.word_box_width,
                user_selected_box.word_box_height,
                user_selected_box.word_box_angle,
            ]
        return text_to_send

    @api.model
    def _cron_validate(self):
        validated = super()._cron_validate()
        validated.mapped('extract_word_ids').unlink()  # We don't need word data anymore, we can delete them
        return validated

    def _post(self, soft=True):
        # OVERRIDE
        # On the validation of an invoice, send the different corrected fields to iap to improve the ocr algorithm.
        posted = super()._post(soft)
        self._validate_ocr()
        return posted

    def get_boxes(self):
        return [{
            "id": data.id,
            "feature": data.field,
            "text": data.word_text,
            "ocr_selected": data.ocr_selected,
            "user_selected": data.user_selected,
            "page": data.word_page,
            "box_midX": data.word_box_midX,
            "box_midY": data.word_box_midY,
            "box_width": data.word_box_width,
            "box_height": data.word_box_height,
            "box_angle": data.word_box_angle} for data in self.extract_word_ids]

    def set_user_selected_box(self, id):
        """Set the selected box for a feature. The id of the box indicates the concerned feature.
        The method returns the text that can be set in the view (possibly different of the text in the file)"""
        self.ensure_one()
        word = self.env["account.invoice_extract.words"].browse(int(id))
        to_unselect = self.env["account.invoice_extract.words"].search([("invoice_id", "=", self.id), ("field", "=", word.field), ("user_selected", "=", True)])
        for box in to_unselect:
            box.user_selected = False

        word.user_selected = True
        if word.field == "currency":
            text = word.word_text
            currency = None
            currencies = self.env["res.currency"].search([])
            for curr in currencies:
                if text == curr.currency_unit_label:
                    currency = curr
                if text == curr.name or text == curr.symbol:
                    currency = curr
            if currency:
                return currency.id
            return self.currency_id.id
        if word.field == "VAT_Number":
            partner_vat = False
            if word.word_text != "":
                partner_vat = self._find_partner_id_with_vat(word.word_text)
            if partner_vat:
                return partner_vat.id
            else:
                vat = word.word_text
                partner = self._create_supplier_from_vat(vat)
                return partner.id if partner else False

        if word.field == "supplier":
            return self._find_partner_id_with_name(word.word_text)
        return word.word_text

    def _find_partner_from_previous_extracts(self):
        """
        Try to find the partner according to the detected layout.
        It is expected that two invoices emitted by the same supplier will share the same detected layout.
        """
        match_conditions = [
            ('extract_detected_layout', '=', self.extract_detected_layout),
            ('extract_partner_name', '=', self.extract_partner_name),
        ]
        for condition in match_conditions:
            invoice_layout = self.search([
                condition,
                ('extract_state', '=', 'done'),
                ('move_type', '=', self.move_type),
                ('company_id', '=', self.company_id.id),
            ], limit=1000, order='id desc')
            if invoice_layout:
                break

        # Keep only if we have just one result
        if len(invoice_layout.mapped('partner_id')) == 1:
            return invoice_layout.partner_id
        return None

    def _find_partner_id_with_vat(self, vat_number_ocr):
        partner_vat = self.env["res.partner"].search([
            *self.env['res.partner']._check_company_domain(self.company_id),
            ("vat", "=ilike", vat_number_ocr),
        ], limit=1)
        if not partner_vat:
            partner_vat = self.env["res.partner"].search([
                *self.env['res.partner']._check_company_domain(self.company_id),
                ("vat", "=ilike", vat_number_ocr[2:]),
            ], limit=1)
        if not partner_vat:
            for partner in self.env["res.partner"].search([
                *self.env['res.partner']._check_company_domain(self.company_id),
                ("vat", "!=", False),
            ], limit=1000):
                vat = partner.vat.upper()
                vat_cleaned = vat.replace("BTW", "").replace("MWST", "").replace("ABN", "")
                vat_cleaned = re.sub(r'[^A-Z0-9]', '', vat_cleaned)
                if vat_cleaned == vat_number_ocr or vat_cleaned == vat_number_ocr[2:]:
                    partner_vat = partner
                    break
        return partner_vat

    def _create_supplier_from_vat(self, vat_number_ocr):
        try:
            response, error = self.env['iap.autocomplete.api']._request_partner_autocomplete(
                action='enrich',
                params={'vat': vat_number_ocr},
            )
            if error:
                raise Exception(error)
            if 'credit_error' in response and response['credit_error']:
                _logger.warning("Credit error on partner_autocomplete call")
        except KeyError:
            _logger.warning("Partner autocomplete isn't installed, supplier creation from VAT is disabled")
            return False
        except Exception as exception:
            _logger.error('Check VAT error: %s' % str(exception))
            return False

        if response and response.get('company_data'):
            country_id = self.env['res.country'].search([('code', '=', response.get('company_data').get('country_code',''))])
            state_id = self.env['res.country.state'].search([('name', '=', response.get('company_data').get('state_name',''))])
            resp_values = response.get('company_data')

            values = {field: resp_values[field] for field in ('name', 'vat', 'street', 'city', 'zip', 'phone', 'email', 'partner_gid') if field in resp_values}
            values['is_company'] = True

            if 'bank_ids' in resp_values:
                values['bank_ids'] = [(0, 0, vals) for vals in resp_values['bank_ids']]

            if country_id:
                values['country_id'] = country_id.id
                if state_id:
                    values['state_id'] = state_id.id

            new_partner = self.env["res.partner"].with_context(clean_context(self.env.context)).create(values)
            return new_partner
        return False

    def _find_partner_id_with_name(self, partner_name):
        if not partner_name:
            return 0

        partner = self.env["res.partner"].search([
            *self.env['res.partner']._check_company_domain(self.company_id),
            ("name", "=", partner_name),
        ], order='supplier_rank desc', limit=1)
        if partner:
            return partner.id if partner.id != self.company_id.partner_id.id else 0

        self.env.cr.execute(*self.env['res.partner']._where_calc([
            *self.env['res.partner']._check_company_domain(self.company_id),
            ('active', '=', True),
            ('name', '!=', False),
            ('supplier_rank', '>', 0),
        ]).select('res_partner.id', 'res_partner.name'))

        partners_dict = {name.lower().replace('-', ' '): partner_id for partner_id, name in self.env.cr.fetchall()}
        partner_name = partner_name.lower().strip()

        partners = {}
        for single_word in [word for word in re.findall(r"\w+", partner_name) if len(word) >= 3]:
            partners_matched = [partner for partner in partners_dict if single_word in partner.split()]
            for partner in partners_matched:
                # Record only if the whole sequence is a very close match
                if SequenceMatcher(None, partner.lower(), partner_name.lower()).ratio() > 0.8:
                    partners[partner] = partners[partner] + 1 if partner in partners else 1

        if partners:
            sorted_partners = sorted(partners, key=partners.get, reverse=True)
            if len(sorted_partners) == 1 or partners[sorted_partners[0]] != partners[sorted_partners[1]]:
                partner = sorted_partners[0]
                if partners_dict[partner] != self.company_id.partner_id.id:
                    return partners_dict[partner]
        return 0

    def _find_partner_with_iban(self, iban_ocr, partner_name):
        bank_accounts = self.env['res.partner.bank'].search([
            *self.env['res.partner.bank']._check_company_domain(self.company_id),
            ('acc_number', '=ilike', iban_ocr),
        ])

        bank_account_match_ratios = sorted([
            (account, SequenceMatcher(None, partner_name.lower(), account.partner_id.name.lower()).ratio())
            for account in bank_accounts
        ], key=lambda x: x[1], reverse=True)

        # Take the partner with the closest name match.
        # The IBAN should be safe enough to avoid false positives, but better safe than sorry.
        if bank_account_match_ratios and bank_account_match_ratios[0][1] > 0.3:
            return bank_account_match_ratios[0][0].partner_id
        return None

    def _get_partner(self, ocr_results):
        vat_number_ocr = self._get_ocr_selected_value(ocr_results, 'VAT_Number', "")
        iban_ocr = self._get_ocr_selected_value(ocr_results, 'iban', "")

        if vat_number_ocr:
            partner_vat = self._find_partner_id_with_vat(vat_number_ocr)
            if partner_vat:
                return partner_vat, False

        if self.is_purchase_document() and self.extract_detected_layout:
            partner = self._find_partner_from_previous_extracts()
            if partner:
                return partner, False

        if self.is_purchase_document() and iban_ocr:
            partner = self._find_partner_with_iban(iban_ocr, self.extract_partner_name)
            if partner:
                return partner, False

        partner_id = self._find_partner_id_with_name(self.extract_partner_name)
        if partner_id != 0:
            return self.env["res.partner"].browse(partner_id), False

        # Create a partner from the VAT number
        if vat_number_ocr:
            created_supplier = self._create_supplier_from_vat(vat_number_ocr)
            if created_supplier:
                return created_supplier, True
        return False, False

    def _get_taxes_record(self, taxes_ocr, taxes_type_ocr):
        """
        Find taxes records to use from the taxes detected for an invoice line.
        """
        taxes_found = self.env['account.tax']
        type_tax_use = 'purchase' if self.is_purchase_document() else 'sale'
        if self.is_indian_taxes() and len(taxes_ocr) > 1:
            total_tax = sum(taxes_ocr)
            grouped_taxes_records = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(self.company_id),
                ('amount', '=', total_tax),
                ('amount_type', '=', 'group'),
                ('type_tax_use', '=', type_tax_use),
            ])
            for grouped_tax in grouped_taxes_records:
                children_taxes = grouped_tax.children_tax_ids.mapped('amount')
                if set(taxes_ocr) == set(children_taxes):
                    return grouped_tax
        for (taxes, taxes_type) in zip(taxes_ocr, taxes_type_ocr):
            if taxes != 0.0:
                related_documents = self.env['account.move'].search([
                    ('state', '!=', 'draft'),
                    ('move_type', '=', self.move_type),
                    ('partner_id', '=', self.partner_id.id),
                    ('company_id', '=', self.company_id.id),
                ], limit=100, order='id desc')
                lines = related_documents.mapped('invoice_line_ids')
                taxes_ids = related_documents.mapped('invoice_line_ids.tax_ids')
                taxes_ids = taxes_ids.filtered(
                    lambda tax:
                        tax.active and
                        tax.amount == taxes and
                        tax.amount_type == taxes_type and
                        tax.type_tax_use == type_tax_use
                )
                taxes_by_document = []
                for tax in taxes_ids:
                    taxes_by_document.append((tax, lines.filtered(lambda line: tax in line.tax_ids)))
                if len(taxes_by_document) != 0:
                    taxes_found |= max(taxes_by_document, key=lambda tax: len(tax[1]))[0]
                else:
                    tax_domain = [
                        *self.env['account.tax']._check_company_domain(self.company_id),
                        ('amount', '=', taxes),
                        ('amount_type', '=', taxes_type),
                        ('type_tax_use', '=', type_tax_use),
                    ]
                    default_taxes = self.journal_id.default_account_id.tax_ids
                    matching_default_tax = default_taxes.filtered_domain(tax_domain)
                    if matching_default_tax:
                        taxes_found |= matching_default_tax
                    else:
                        taxes_records = self.env['account.tax'].search(tax_domain)
                        if taxes_records:
                            taxes_records_setting_based = taxes_records.filtered(lambda r: not r.price_include)
                            if taxes_records_setting_based:
                                taxes_record = taxes_records_setting_based[0]
                            else:
                                taxes_record = taxes_records[0]
                            taxes_found |= taxes_record
        return taxes_found

    def _get_currency(self, currency_ocr, partner_id):
        for comparison in ['=ilike', 'ilike']:
            possible_currencies = self.env["res.currency"].search([
                '|', '|',
                ('currency_unit_label', comparison, currency_ocr),
                ('name', comparison, currency_ocr),
                ('symbol', comparison, currency_ocr),
            ])
            if possible_currencies:
                break

        partner_last_invoice_currency = partner_id.invoice_ids[:1].currency_id
        if partner_last_invoice_currency in possible_currencies:
            return partner_last_invoice_currency
        if self.company_id.currency_id in possible_currencies:
            return self.company_id.currency_id
        return possible_currencies if len(possible_currencies) == 1 else None


    def _get_invoice_lines(self, ocr_results):
        """
        Get write values for invoice lines.
        """
        self.ensure_one()

        invoice_lines = ocr_results.get('invoice_lines', [])
        subtotal_ocr = self._get_ocr_selected_value(ocr_results, 'subtotal', 0.0)
        supplier_ocr = self._get_ocr_selected_value(ocr_results, 'supplier', "")
        date_ocr = self._get_ocr_selected_value(ocr_results, 'date', "")

        invoice_lines_to_create = []
        if self.company_id.extract_single_line_per_tax:
            merged_lines = {}
            for il in invoice_lines:
                total = self._get_ocr_selected_value(il, 'total', 0.0)
                subtotal = self._get_ocr_selected_value(il, 'subtotal', total)
                taxes_ocr = [value['content'] for value in il.get('taxes', {}).get('selected_values', [])]
                taxes_type_ocr = [value.get('amount_type', 'percent') for value in il.get('taxes', {}).get('selected_values', [])]
                taxes_records = self._get_taxes_record(taxes_ocr, taxes_type_ocr)

                if not taxes_records and taxes_ocr:
                    taxes_ids = ('not found', *sorted(taxes_ocr))
                else:
                    taxes_ids = ('found', *sorted(taxes_records.ids))

                if taxes_ids not in merged_lines:
                    merged_lines[taxes_ids] = {'subtotal': subtotal}
                else:
                    merged_lines[taxes_ids]['subtotal'] += subtotal
                merged_lines[taxes_ids]['taxes_records'] = taxes_records

            # if there is only one line after aggregating the lines, use the total found by the ocr as it is less error-prone
            if len(merged_lines) == 1:
                merged_lines[list(merged_lines.keys())[0]]['subtotal'] = subtotal_ocr

            description_fields = []
            if supplier_ocr:
                description_fields.append(supplier_ocr)
            if date_ocr:
                description_fields.append(date_ocr.split()[0])
            description = ' - '.join(description_fields)

            for il in merged_lines.values():
                vals = {
                    'name': description,
                    'price_unit': il['subtotal'],
                    'quantity': 1.0,
                    'tax_ids': il['taxes_records'],
                }

                invoice_lines_to_create.append(vals)
        else:
            for il in invoice_lines:
                description = self._get_ocr_selected_value(il, 'description', "/")
                total = self._get_ocr_selected_value(il, 'total', 0.0)
                subtotal = self._get_ocr_selected_value(il, 'subtotal', total)
                unit_price = self._get_ocr_selected_value(il, 'unit_price', subtotal)
                quantity = self._get_ocr_selected_value(il, 'quantity', 1.0)
                taxes_ocr = [value['content'] for value in il.get('taxes', {}).get('selected_values', [])]
                taxes_type_ocr = [value.get('amount_type', 'percent') for value in il.get('taxes', {}).get('selected_values', [])]

                vals = {
                    'name': description,
                    'price_unit': unit_price,
                    'quantity': quantity,
                    'tax_ids': self._get_taxes_record(taxes_ocr, taxes_type_ocr)
                }

                invoice_lines_to_create.append(vals)

        return invoice_lines_to_create

    def _fill_document_with_results(self, ocr_results, force_write=False):
        if self.state != 'draft' or ocr_results is None:
            return

        if 'detected_layout_id' in ocr_results:
            self.extract_detected_layout = ocr_results['detected_layout_id']

        if ocr_results.get('type') == 'refund' and self.move_type in ('in_invoice', 'out_invoice'):
            # We only switch from an invoice to a credit note, not the other way around.
            # We assume that if the user has specifically created a credit note, it is indeed a credit note.
            self.action_switch_move_type()

        self._save_form(ocr_results, force_write=force_write)

        if self.extract_word_ids:  # We don't want to recreate the boxes when the user clicks on "Reload AI data"
            return

        fields_with_boxes = ['supplier', 'date', 'due_date', 'invoice_id', 'currency', 'VAT_Number', 'total']
        for field in filter(ocr_results.get, fields_with_boxes):
            value = ocr_results[field]
            selected_value = value.get('selected_value')
            data = []

            # We need to make sure that only one candidate is selected.
            # Once this flag is set, the next candidates can't be set as selected.
            ocr_chosen_candidate_found = False
            for candidate in value.get('candidates', []):
                ocr_chosen = selected_value == candidate and not ocr_chosen_candidate_found
                if ocr_chosen:
                    ocr_chosen_candidate_found = True
                data.append((0, 0, {
                    "field": field,
                    "ocr_selected": ocr_chosen,
                    "user_selected": ocr_chosen,
                    "word_text": candidate['content'],
                    "word_page": candidate['page'],
                    "word_box_midX": candidate['coords'][0],
                    "word_box_midY": candidate['coords'][1],
                    "word_box_width": candidate['coords'][2],
                    "word_box_height": candidate['coords'][3],
                    "word_box_angle": candidate['coords'][4],
                }))
            self.write({'extract_word_ids': data})

    def _save_form(self, ocr_results, force_write=False):
        date_ocr = self._get_ocr_selected_value(ocr_results, 'date', "")
        due_date_ocr = self._get_ocr_selected_value(ocr_results, 'due_date', "")
        total_ocr = self._get_ocr_selected_value(ocr_results, 'total', 0.0)
        invoice_id_ocr = self._get_ocr_selected_value(ocr_results, 'invoice_id', "")
        currency_ocr = self._get_ocr_selected_value(ocr_results, 'currency', "")
        payment_ref_ocr = self._get_ocr_selected_value(ocr_results, 'payment_ref', "")
        iban_ocr = self._get_ocr_selected_value(ocr_results, 'iban', "")
        SWIFT_code_ocr = json.loads(self._get_ocr_selected_value(ocr_results, 'SWIFT_code', "{}")) or None
        qr_bill_ocr = self._get_ocr_selected_value(ocr_results, 'qr-bill')
        supplier_ocr = self._get_ocr_selected_value(ocr_results, 'supplier', "")
        client_ocr = self._get_ocr_selected_value(ocr_results, 'client', "")
        total_tax_amount_ocr = self._get_ocr_selected_value(ocr_results, 'total_tax_amount', 0.0)

        self.extract_partner_name = client_ocr if self.is_sale_document() else supplier_ocr

        with self._get_edi_creation() as move_form:
            if not move_form.partner_id:
                partner_id, created = self._get_partner(ocr_results)
                if partner_id:
                    move_form.partner_id = partner_id
                    if created and iban_ocr and not move_form.partner_bank_id and self.is_purchase_document():
                        bank_account = self.env['res.partner.bank'].search([
                            *self.env['res.partner.bank']._check_company_domain(self.company_id),
                            ('acc_number', '=ilike', iban_ocr),
                        ])
                        if bank_account:
                            if bank_account.partner_id == move_form.partner_id.id:
                                move_form.partner_bank_id = bank_account
                        else:
                            vals = {
                                'partner_id': move_form.partner_id.id,
                                'acc_number': iban_ocr
                            }
                            if SWIFT_code_ocr:
                                bank_id = self.env['res.bank'].search([('bic', '=', SWIFT_code_ocr['bic'])], limit=1)
                                if bank_id:
                                    vals['bank_id'] = bank_id.id
                                if not bank_id and SWIFT_code_ocr['verified_bic']:
                                    country_id = self.env['res.country'].search([('code', '=', SWIFT_code_ocr['country_code'])], limit=1)
                                    if country_id:
                                        vals['bank_id'] = self.env['res.bank'].create({'name': SWIFT_code_ocr['name'], 'country': country_id.id, 'city': SWIFT_code_ocr['city'], 'bic': SWIFT_code_ocr['bic']}).id
                            move_form.partner_bank_id = self.with_context(clean_context(self.env.context)).env['res.partner.bank'].create(vals)

            if qr_bill_ocr:
                qr_content_list = qr_bill_ocr.splitlines()
                # Supplier and client sections have an offset of 16
                index_offset = 16 if self.is_sale_document() else 0
                if not move_form.partner_id:
                    partner_name = qr_content_list[5 + index_offset]
                    move_form.partner_id = self.env["res.partner"].with_context(clean_context(self.env.context)).create({
                        'name': partner_name,
                        'is_company': True,
                    })

                partner = move_form.partner_id
                address_type = qr_content_list[4 + index_offset]
                if address_type == 'S':
                    if not partner.street:
                        street = qr_content_list[6 + index_offset]
                        house_nb = qr_content_list[7 + index_offset]
                        partner.street = " ".join((street, house_nb))

                    if not partner.zip:
                        partner.zip = qr_content_list[8 + index_offset]

                    if not partner.city:
                        partner.city = qr_content_list[9 + index_offset]

                elif address_type == 'K':
                    if not partner.street:
                        partner.street = qr_content_list[6 + index_offset]
                        partner.street2 = qr_content_list[7 + index_offset]

                country_code = qr_content_list[10 + index_offset]
                if not partner.country_id and country_code:
                    country = self.env['res.country'].search([('code', '=', country_code)])
                    partner.country_id = country and country.id

                if self.is_purchase_document():
                    iban = qr_content_list[3]
                    if iban and not self.env['res.partner.bank'].search([('acc_number', '=ilike', iban)]):
                        move_form.partner_bank_id = self.with_context(clean_context(self.env.context)).env['res.partner.bank'].create({
                            'acc_number': iban,
                            'company_id': move_form.company_id.id,
                            'currency_id': move_form.currency_id.id,
                            'partner_id': partner.id,
                        })

            due_date_move_form = move_form.invoice_date_due  # remember the due_date, as it could be modified by the onchange() of invoice_date
            context_create_date = fields.Date.context_today(self, self.create_date)
            if date_ocr and (not move_form.invoice_date or move_form.invoice_date == context_create_date):
                move_form.invoice_date = date_ocr
            if due_date_ocr and due_date_move_form == context_create_date:
                if date_ocr == due_date_ocr and move_form.partner_id and move_form.partner_id.property_supplier_payment_term_id:
                    # if the invoice date and the due date found by the OCR are the same, we use the payment terms of the detected supplier instead, if there is one
                    move_form.invoice_payment_term_id = move_form.partner_id.property_supplier_payment_term_id
                else:
                    move_form.invoice_date_due = due_date_ocr

            if self.is_purchase_document() and not move_form.ref:
                move_form.ref = invoice_id_ocr

            if self.is_sale_document() and self.quick_edit_mode:
                move_form.name = invoice_id_ocr

            if payment_ref_ocr and not move_form.payment_reference:
                move_form.payment_reference = payment_ref_ocr

            add_lines = not move_form.invoice_line_ids
            if add_lines:
                if currency_ocr and move_form.currency_id == move_form.company_currency_id:
                    currency = self._get_currency(currency_ocr, move_form.partner_id)
                    if currency:
                        move_form.currency_id = currency

                vals_invoice_lines = self._get_invoice_lines(ocr_results)
                # Create the lines with only the name for account_predictive_bills
                move_form.invoice_line_ids = [
                    Command.create({'name': line_vals.pop('name')})
                    for line_vals in vals_invoice_lines
                ]

        if add_lines:
            # We needed to close the first _get_edi_creation context to let account_predictive_bills do the predictions based on the label
            with self._get_edi_creation() as move_form:
                # Now edit them with the correct amount and apply the taxes
                for line, ocr_line_vals in zip(move_form.invoice_line_ids[-len(vals_invoice_lines):], vals_invoice_lines):
                    line.write({
                        'price_unit': ocr_line_vals['price_unit'],
                        'quantity': ocr_line_vals['quantity'],
                    })
                    taxes_dict = {}
                    for tax in line.tax_ids:
                        taxes_dict[(tax.amount, tax.amount_type, tax.price_include)] = {
                            'found_by_OCR': False,
                            'tax_record': tax,
                        }
                    for taxes_record in ocr_line_vals['tax_ids']:
                        tax_tuple = (taxes_record.amount, taxes_record.amount_type, taxes_record.price_include)
                        if tax_tuple not in taxes_dict:
                            line.tax_ids = [Command.link(taxes_record.id)]
                        else:
                            taxes_dict[tax_tuple]['found_by_OCR'] = True
                        if taxes_record.price_include:
                            line.price_unit *= 1 + taxes_record.amount / 100
                    for tax_info in taxes_dict.values():
                        if not tax_info['found_by_OCR']:
                            amount_before = line.price_total
                            line.tax_ids = [Command.unlink(tax_info['tax_record'].id)]
                            # If the total amount didn't change after removing it, we can actually leave it.
                            # This is intended as a way to keep intra-community taxes
                            if line.price_total == amount_before:
                                line.tax_ids = [Command.link(tax_info['tax_record'].id)]

            # Check the tax roundings after the tax lines have been synced
            tax_amount_rounding_error = total_ocr - self.tax_totals['amount_total']
            threshold = len(vals_invoice_lines) * move_form.currency_id.rounding
            # Check if tax amounts detected by the ocr are correct and
            # replace the taxes that caused the rounding error in case of indian localization
            if not move_form.currency_id.is_zero(tax_amount_rounding_error) and self.is_indian_taxes():
                fixed_rounding_error = total_ocr - total_tax_amount_ocr - self.tax_totals['amount_untaxed']
                tax_totals = self.tax_totals
                tax_groups = tax_totals['groups_by_subtotal']['Untaxed Amount']
                if move_form.currency_id.is_zero(fixed_rounding_error) and tax_groups:
                    tax = total_tax_amount_ocr / len(tax_groups)
                    for tax_total in tax_groups:
                        tax_total.update({
                            'tax_group_amount': tax,
                            'formatted_tax_group_amount': formatLang(self.env, tax, currency_obj=self.currency_id),
                        })
                    self.tax_totals = tax_totals

            if (
                not move_form.currency_id.is_zero(tax_amount_rounding_error) and
                float_compare(abs(tax_amount_rounding_error), threshold, precision_digits=2) <= 0
            ):
                self._check_total_amount(total_ocr)

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    @api.model
    def _import_invoice_ocr(self, invoice, file_data, new=False):
        invoice.message_main_attachment_id = file_data['attachment']
        invoice._send_batch_for_digitization()
        return True

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        self.ensure_one()

        if file_data['type'] in ('pdf', 'binary') and self._needs_auto_extract(new_document=new, file_type=file_data['type']):
            return self._import_invoice_ocr
        return super()._get_edi_decoder(file_data, new=new)
