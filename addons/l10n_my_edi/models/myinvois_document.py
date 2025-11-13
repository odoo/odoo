# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime
import re
import time
from collections import defaultdict

import dateutil
import werkzeug
from lxml import etree

from odoo import SUPERUSER_ID, api, fields, models, modules
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import config, date_utils, split_every
from odoo.tools.image import image_data_uri

from odoo.addons.account.tools import dict_to_xml

# Holds the maximum amount of records that can be sent in a single submission.
SUBMISSION_MAX_SIZE = 100
MAX_SUBMISSION_UPDATE = 25
CANCELLED_STATES = {'invalid', 'cancelled'}


class MyInvoisDocument(models.Model):
    """
    Represents a single document on the MyInvois platform.

    In Odoo, a document represent either an invoice, or a group of PoS order.
    """
    _name = 'myinvois.document'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = "MyInvois Document"
    _order = "myinvois_issuance_date desc, id desc"
    _check_company_auto = True
    _sequence_date_field = "myinvois_issuance_date"

    # ------------------
    # Fields declaration
    # ------------------

    name = fields.Char(
        compute='_compute_name',
        store=True,
        copy=False,
        index='trigram',
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
    )
    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id',
    )
    myinvois_issuance_date = fields.Date(
        string="Issuance Date",
        readonly=True,
        copy=False,
    )
    # File fields
    myinvois_file_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute=lambda self: self._compute_linked_attachment_id('myinvois_file_id', 'myinvois_file'),
        depends=['myinvois_file'],
        copy=False,
        export_string_translation=False,
    )
    myinvois_file = fields.Binary(
        string='MyInvois XML File',
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    # Odoo Implementation fields
    myinvois_state = fields.Selection(
        string='MyInvois State',
        help='State of this document on the MyInvois portal.\nA document awaiting validation will be automatically updated once the validation status is available.',
        selection=[
            ('in_progress', 'Validation In Progress'),
            ('valid', 'Valid'),
            ('rejected', 'Rejected'),  # Technically not a state on MyInvois, but having it here helps with managing bills.
            ('invalid', 'Invalid'),
            ('cancelled', 'Cancelled'),
        ],
        copy=False,
        readonly=True,
        tracking=True,
    )
    myinvois_error_document_hash = fields.Char(
        string="Document Hash",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    myinvois_retry_at = fields.Char(
        string="Document Retry At",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    myinvois_exemption_reason = fields.Char(
        string="Tax Exemption Reason",
        help="Buyer’s sales tax exemption certificate number, special exemption as per gazette orders, etc.\n"
             "Only applicable if you are using a tax with a type 'Exempt'.",
    )
    myinvois_custom_form_reference = fields.Char(
        string="Customs Form Reference Number",
        help="Reference Number of Customs Form No.1, 9, etc.",
    )
    # API information fields
    myinvois_submission_uid = fields.Char(
        string='Submission UID',
        help="Unique ID assigned to a batch of documents when sent to MyInvois.",
        copy=False,
        readonly=True,
    )
    myinvois_external_uuid = fields.Char(
        string="MyInvois ID",
        help="Unique ID assigned to a specific document when sent to MyInvois.",
        copy=False,
        index=True,
        readonly=True,
    )
    myinvois_validation_time = fields.Datetime(
        string='Validation Time',
        copy=False,
        readonly=True,
    )
    myinvois_document_long_id = fields.Char(
        string="MyInvois Long ID",
        copy=False,
        readonly=True,
    )
    # Note: the field is present but unused for now.
    invoice_ids = fields.Many2many(
        name="Invoices",
        comodel_name="account.move",
        relation="myinvois_document_invoice_rel",
        column1="document_id",
        column2="invoice_id",
        check_company=True,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('myinvois_issuance_date')
    def _compute_name(self):
        """ Compute the name by using the sequence mixin. """
        for document in self.sorted(key=lambda d: (d.myinvois_issuance_date, d._origin.id)):
            document_has_name = document.name and document.name != '/'
            if document_has_name:
                if not document._sequence_matches_date():
                    document.name = False
                    continue
            if document.myinvois_issuance_date and not document_has_name:
                document._set_next_sequence()

        self.filtered(lambda m: not m.name).name = '/'

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        """
        Helper to retrieve Attachment from Binary fields
        This is needed because fields.Many2one('ir.attachment') makes all
        attachments available to the user.
        """
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('res_field', '=', binary_field),
        ])
        attachments_per_res_id = attachments.grouped('res_id')
        for document in self:
            document[attachment_field] = attachments_per_res_id.get(document._origin.id, False)

    @api.depends('name')
    def _compute_display_name(self):
        for document in self:
            document.display_name = document.name if document.name != '/' else document.env._('Draft')

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _get_starting_sequence(self):
        """ Defines the default sequence to use by MyInvois Documents. """
        self.ensure_one()
        return "MYINV/%04d/00000" % self.myinvois_issuance_date.year

    def _get_last_sequence_domain(self, relaxed=False):
        """ Returns the SQL WHERE statement to use when fetching the latest record with the same sequence, and its params. """
        self.ensure_one()
        if not self.myinvois_issuance_date:
            return "WHERE FALSE", {}
        where_string = "WHERE name != '/'"
        param = {}

        if not relaxed:
            domain = [('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            reference_name = self.sudo().search(domain + [('myinvois_issuance_date', '<=', self.myinvois_issuance_date)], limit=1).name
            if not reference_name:
                reference_name = self.sudo().search(domain, order='myinvois_issuance_date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_name)
            date_start, date_end, *_ = self._get_sequence_date_range(sequence_number_reset)
            where_string += """ AND myinvois_issuance_date BETWEEN %(date_start)s AND %(date_end)s"""
            param['date_start'] = date_start
            param['date_end'] = date_end
            if sequence_number_reset in ('year', 'year_range'):
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'never':
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

            if param.get('anti_regex'):
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        return where_string, param

    def _get_sequence_date_range(self, reset):
        """ Make sure that the sequence date range follows the company's fiscal year """
        if reset == 'year_range':
            company = self.company_id
            return date_utils.get_fiscal_year(self.myinvois_issuance_date, day=company.fiscalyear_last_day, month=int(company.fiscalyear_last_month))
        return super()._get_sequence_date_range(reset)

    @api.ondelete(at_uninstall=False)
    def _unlink_check(self):
        for document in self:
            if document.myinvois_state in ["in_progress", "valid", "rejected"]:
                raise UserError(document.env._('You cannot delete a document that is active on MyInvois.\nYou must cancel it first.'))

    # --------------
    # Action methods
    # --------------

    def action_submit_to_myinvois(self):
        """
        Submit all new documents in self to MyInvois.
        This can also be used on invalid documents to re-submit them after correcting the error.
        """
        documents = self.filtered(lambda d: d.myinvois_state in [False, 'invalid'])
        if not documents:
            return

        # Documents linked to an invoice, and whose invoice is cancelled or draft, shouldn't be sent.
        invalid_documents = documents.filtered(lambda d: d.invoice_ids and any(invoice.state in ('draft', 'cancel') for invoice in d.invoice_ids))
        if invalid_documents:
            raise UserError(self.env._('You cannot send this document to MyInvois because the related invoice(s) %s are in draft or canceled state.', ','.join(invalid_documents.mapped('name'))))

        # Required for the file, this is the exact date at which the consolidated invoice was sent to MyInvois.
        documents.myinvois_issuance_date = fields.Date.context_today(documents)
        documents._submit_to_myinvois()

    def action_update_submission_status(self):
        """
        Fetches the status of all the documents in self.
        Note that the endpoint reached to do so will differ based on the amount of documents in the recordset.
        """
        if len(self) == 1:
            self._myinvois_single_status_update()
        else:
            self._myinvois_submission_statuses_update()

    def action_generate_xml_file(self):
        """
        Generate a xml file for each of the MyInvois documents in self.
        If the document already as a file, the previous file's name is updated to include an (old) tag to avoid confusion in the attachment list.
        """
        new_documents_data = []
        for document in self:
            if document.myinvois_file_id:
                document.myinvois_file_id.write({
                    'name': f"{document.myinvois_file_id.name} (old)",
                    'res_field': False,  # Remove the link between the old attachment and the record's field
                })

            xml_data, errors = document._myinvois_generate_xml_file()
            if errors:
                raise UserError(document.env._("Error when generating the documents' files:\n\n- %(errors)s", errors='\n- '.join(errors)))

            new_documents_data.append({
                "name": f'{document.name.replace("/", "_")}_myinvois.xml' if document.name != "/" else "myinvois.xml",
                "raw": xml_data,
                "mimetype": "application/xml",
                "res_model": document._name,
                "res_id": document.id,
                "res_field": "myinvois_file",
            })

        self.env["ir.attachment"].with_user(SUPERUSER_ID).create(new_documents_data)
        self.invalidate_recordset(fnames=['myinvois_file_id', 'myinvois_file'])

    def action_cancel_submission(self):
        """ Cancel the document on the platform. """
        self.ensure_one()
        return self._action_myinvois_update_document(new_status='cancelled')

    def action_show_myinvois_documents(self):
        """ Open the documents in self in the correct view based on the amount of records. """
        if len(self) == 1:
            action_vals = {
                'type': 'ir.actions.act_window',
                'res_model': 'myinvois.document',
                'view_mode': 'form',
                'res_id': self.id,
                'views': [(self.env.ref('l10n_my_edi.myinvois_document_form_view').id, 'form')],
            }
        else:
            action_vals = {
                'name': self.env._("Consolidated Invoices"),
                'type': 'ir.actions.act_window',
                'res_model': 'myinvois.document',
                'view_mode': 'list,form',
                'views': [(self.env.ref('l10n_my_edi.myinvois_document_list_view').id, 'list'), (self.env.ref('l10n_my_edi.myinvois_document_form_view').id, 'form')],
                'domain': [('id', 'in', self.ids)],
            }
        return action_vals

    # ----------------
    # Business methods
    # ----------------

    # Most of the logic here is written to work regardless of the linked document;

    def _myinvois_get_proxy_user(self):
        """
        Models implementing the mixin should define the logic to get the record's proxy user here.
        Typically, the one linked to the record's company.
        :return: The proxy user that should be used to send the record to MyInvois.
        """
        self.ensure_one()
        company = self.company_id or self.env.company

        proxy_user = company.sudo().l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(self.env._("Please register for the E-Invoicing service in the settings first."))

        return proxy_user

    def _myinvois_log_message(self, message=None, bodies=None):
        """
        Small helper to use when logging in the chatter to automatically broadcast the message to the invoice.

        Supports receiving a simple message string, or a dict of bodies targeted to self.
        """
        if message:
            self._message_log_batch(bodies={document.id: message for document in self})
            if self.invoice_ids:
                self.invoice_ids._message_log_batch(bodies={move.id: message for move in self.invoice_ids})

        documents_per_id = self.grouped('id')
        if bodies:
            self._message_log_batch(bodies=bodies)
            if self.invoice_ids:
                invoice_bodies = {}
                for document_id, message in bodies.items():
                    invoice_bodies.update({invoice.id: message for invoice in documents_per_id[document_id].invoice_ids})
                self.invoice_ids._message_log_batch(bodies=invoice_bodies)

    @api.model
    def _myinvois_map_error(self, error):
        """ This helper will take in an error code coming from the proxy, and return a translatable error message. """
        error_map = {
            # These errors should be returned when we send malformed request to the EDI, ... tldr; this should never happen unless we have bugs.
            "internal_server_error": self.env._(
                "Server error; If the problem persists, please contact the Odoo support."
            ),
            # The proxy user credentials are either incorrect, or Odoo does not have the permission to invoice on their behalf.
            "invalid_tin": self.env._(
                "Please make sure that your company TIN is correct, and that you gave Odoo sufficient permissions on the MyInvois platform."
            ),
            # The api rate limit has been reached. If this happens, we need to ask the user to wait. This is also handled proxy side to be safe
            "rate_limit_exceeded": self.env._(
                "The api request limit has been reached. Please wait until %(limit_reset_datetime)s to try again.",
                limit_reset_datetime=error.get("data"),
            ),  # Note, should be UTC. The TZ name is present in the formatted date.
            "hash_resubmitted": self.env._(
                "This document has already been submitted and was deemed invalid.\n"
                "Please correct the document based on the previous error, or wait before retrying."
            ),
            # This happens when the MyInvois TIN validator cannot validate the TIN of the user using the provided identification type and number.
            "document_tin_not_found": self.env._(
                "MyInvois could not match your TIN with the identification information you provided on the company."
            ),
            # This happens when the TIN of the supplier doesn't match with the TIN registered on the Proxy. Data contains the TIN.
            "document_tin_mismatch": self.env._(
                "The TIN number of the supplier in the invoices does not match with the one provided at the time of registering for the e-invoice service.\n"
                "If the TIN of the supplier's record changed after that, you will need to archive your EDI Proxy User and re-register.\n"
                "The TIN found in the document is %(tin_number)s",
                tin_number=error.get("data"),
            ),
            # This happens when a batch of invoices contains multiple different identifier for the supplier. Data contains the invoice.
            "multiple_documents_id": self.env._(
                "Multiple different supplier identification information were found in the invoices.\n"
                "If the company identification information changed, you may need to delete your invoice attachments and regenerate them."
            ),
            # Same as the previous error, but with the supplier TIN
            "multiple_documents_tin": self.env._(
                "Multiple different supplier TIN were found in the invoices.\n"
                "If the company TIN changed, you may need to delete your invoice attachments and regenerate them."
            ),
            # You cannot cancel an invoice that has been rejected or that is invalid
            "update_incorrect_state": self.env._(
                "You can only update the status of invoices in the valid state."
            ),
            "update_period_over": self.env._(
                "It has been more than 72h since the invoice validation, you can no longer update it.\n"
                "Instead, you should issue or request a debit or credit note."
            ),
            "update_active_documents": self.env._(
                "You cannot update this invoice, has it has been referenced by a debit or credit note.\n"
                "If you still want to update it, you must first update the debit/credit note."
            ),
            "update_forbidden": self.env._("You do not have the permission to update this invoice."),
            "search_date_invalid": self.env._("The search params are invalid."),  # Should never happen
            'document_not_found': self.env._('The document provided in the request does not exist.'),  # Should never happen
            'submission_too_large': self.env._('The submission is too large, try to send fewer invoices at once.'),
            'action_forbidden': self.env._('Permission to do this action has not been granted. Please ensure that Odoo has sufficient permissions on the MyInvois platform.'),
        }

        if error.get('target'):
            # When validating a part of the invoice, they give random numerical codes with no explanation whatsoever.
            # So instead of trying to guess what they mean, we just give a generic "this is not valid" error and hope for the best.
            # For future bugfixer => To avoid issues as much as possible, please add additional checks in the UBL python file to avoid these.
            return self.env._('An error occurred while validating the invoice: "%(property_name)s" is invalid.', property_name=error['target'])

        return error_map.get(error['reference'], self.env._("An unexpected error has occurred."))

    @staticmethod
    def _can_commit():
        """ Helper to know if we can commit the current transaction or not.

        :returns: True if commit is acceptable, False otherwise.
        """
        return not config['test_enable'] and not modules.module.current_test

    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        # else, attachments with 'res_field' get excluded
        return res | self.myinvois_file_id

    def _get_active_myinvois_document(self, including_in_progress=False):
        """
        Returns the first document in self that is considered active on the platform.
        An active document is a document that has been successfully sent, but no cancelled.

        There are no flows at the moment where we intend to have more than one active document at a time
        for a specific record.

        :param including_in_progress: if set to true, invoices of state in_progress will be included.
        """
        active_states = ['valid', 'rejected'] + (['in_progress'] if including_in_progress else [])
        return self.filtered(lambda d: d.myinvois_state in active_states)[:1]

    def _generate_myinvois_qr_code(self):
        """ Generate the qr code for which can be used to access this document. """
        self.ensure_one()

        if not self.myinvois_document_long_id:  # Only valid invoices have a long id
            return None

        # We need to add the portal url to the qr
        proxy_user = self._myinvois_get_proxy_user()
        if proxy_user.edi_mode == 'prod':
            portal_url = "myinvois.hasil.gov.my"
        else:
            portal_url = "preprod.myinvois.hasil.gov.my"

        try:
            qr_code = self.env['ir.actions.report'].barcode(
                barcode_type='QR',
                width=128,
                height=128,
                humanreadable=1,
                value=f'https://{portal_url}/{self.myinvois_external_uuid}/share/{self.myinvois_document_long_id}',
            )
        except (ValueError, AttributeError):
            raise werkzeug.exceptions.HTTPException(description='Cannot convert into QR Code.')

        return image_data_uri(base64.b64encode(qr_code))

    def _is_refund_document(self):
        """
        :return: True if this document is linked to a single refund invoice.
        """
        has_single_document = self.invoice_ids and len(self.invoice_ids) == 1
        return has_single_document and self.invoice_ids[0].move_type in ('out_refund', 'in_refund')

    def _get_rounded_base_lines(self):
        """
        The base lines used when exporting the document will highly differ based on whether this is
        or not a consolidated invoice, as well as whether this is for PoS.

        :return: The rounded base lines to be used when exporting the document.
        """
        self.ensure_one()
        # Refunds of consolidated invoices are treated as regular invoice besides for the fixed customer.
        if self._is_consolidated_invoice():
            AccountTax = self.env['account.tax']
            grouped_records = self._split_consolidated_invoice_record_in_lines()

            tax_data_fields = (
                "raw_base_amount_currency",
                "raw_base_amount",
                "raw_tax_amount_currency",
                "raw_tax_amount",
                "base_amount_currency",
                "base_amount",
                "tax_amount_currency",
                "tax_amount",
            )
            consolidated_base_lines = []
            for index, records in enumerate(grouped_records):
                base_lines = []
                for record in records:
                    base_lines += self._get_record_rounded_base_lines(record)

                # Aggregate the base lines into one.
                new_tax_details = {
                    "raw_total_excluded_currency": 0.0,
                    "total_excluded_currency": 0.0,
                    "raw_total_excluded": 0.0,
                    "total_excluded": 0.0,
                    "raw_total_included_currency": 0.0,
                    "total_included_currency": 0.0,
                    "raw_total_included": 0.0,
                    "total_included": 0.0,
                    "delta_total_excluded_currency": 0.0,
                    "delta_total_excluded": 0.0,
                }
                new_taxes_data_map = {}

                taxes = self.env["account.tax"]
                for base_line in base_lines:
                    tax_details = base_line["tax_details"]
                    sign = -1 if base_line["is_refund"] else 1
                    for key in new_tax_details:
                        new_tax_details[key] += sign * tax_details[key]
                    for tax_data in tax_details["taxes_data"]:
                        tax = tax_data["tax"]
                        taxes |= tax
                        if tax in new_taxes_data_map:
                            for key in tax_data_fields:
                                new_taxes_data_map[tax][key] += sign * tax_data[key]
                        else:
                            new_taxes_data_map[tax] = dict(tax_data)
                            for key in tax_data_fields:
                                new_taxes_data_map[tax][key] = sign * tax_data[key]

                total_amount_discounted = new_tax_details["total_excluded"] + new_tax_details["delta_total_excluded"]
                total_amount_discounted_currency = new_tax_details["total_excluded_currency"] + new_tax_details["delta_total_excluded_currency"]
                total_amount = total_amount_currency = 0.0
                for base_line in base_lines:
                    sign = -1 if base_line["is_refund"] else 1
                    total_amount += sign * (
                        (base_line["price_unit"] / base_line["rate"])
                        * base_line["quantity"]
                    )
                    total_amount_currency += sign * (
                        base_line["price_unit"] * base_line["quantity"]
                    )

                # for the line name, when consolidating, we want to show first sequence - last sequence
                sequenced_records = records.sorted(key=lambda r: r.name)
                new_base_line = AccountTax._prepare_base_line_for_taxes_computation(
                    {},
                    tax_ids=taxes,
                    price_unit=total_amount_currency,
                    discount_amount=total_amount - total_amount_discounted,
                    discount_amount_currency=total_amount_currency - total_amount_discounted_currency,
                    quantity=1.0,
                    currency_id=self.currency_id,
                    tax_details={
                        **new_tax_details,
                        "taxes_data": list(new_taxes_data_map.values()),
                    },
                    line_name=f"{sequenced_records[0].name}-{sequenced_records[-1].name}" if len(sequenced_records) > 1 else sequenced_records[0].name,
                )
                consolidated_base_lines.append(new_base_line)

            base_lines = consolidated_base_lines
        else:
            invoice = self.invoice_ids[0]  # Otherwise it would be a consolidated invoice.
            base_lines, _tax_lines = invoice._get_rounded_base_and_tax_lines()
        # In any cases, we'll provide a reference to the document in the base lines.
        # This will help later on when it is time to handle tax grouping as we may need to get the
        # tax exemption info.
        for base_line in base_lines:
            base_line['myinvois_document'] = self

        return base_lines

    # Consolidated invoices helpers.

    def _is_consolidated_invoice(self):
        """
        In a few flows, we need to know if we're dealing with a consolidated invoice in order to set
        the correct customer for example.
        This method is here for that; in practice we will be dealing with a consolidated invoice when:
        - The document is linked to multiple records or;
        - The document is a refund/credit note of another document linked to multiple records.

        :return: True if this invoice is a consolidated invoice or the refund of one.
        """
        self.ensure_one()
        return len(self.invoice_ids) > 1

    def _is_consolidated_invoice_refund(self):
        """
        :return: True if this document is a refund specifically for a consolidated invoice.
        """
        is_consolidated_invoice_refund = False
        if self._is_refund_document():
            refunded_invoice = self.invoice_ids.reversed_entry_id
            refunded_document = refunded_invoice.l10n_my_edi_document_ids._get_active_myinvois_document(including_in_progress=True)
            is_consolidated_invoice_refund = len(refunded_document.invoice_ids) > 1
        return is_consolidated_invoice_refund

    def _split_consolidated_invoice_record_in_lines(self):
        """
        When dealing with consolidated invoices, all continuous records are grouped in a single line,
        with a split happening only when the continuity is broken (a document was sent individually,...)

        The role of this method is to handle this grouping so that it can be used later when preparing the
        base lines for export.

        :return: a list of recordset containing the related records split into one recordset per line.
        """
        if not self._is_consolidated_invoice() or not self.invoice_ids:
            return []

        # We will be working on that soon, but for now we do not support it.
        raise NotImplementedError("Support for consolidated invoices in the invoicing app is not yet implemented.")

    def _get_record_rounded_base_lines(self, record):
        """
        Little helper to return the rounded base line for a record.
        It is extracted in order to allow extending the logic to support other business models.
        :param record: The record from which to get the base lines.
        :return: The rounder base line for the provided record.
        """
        self.ensure_one()
        record.ensure_one()
        base_lines = []
        if record and record._name == 'account.move':
            base_lines, _tax_lines = record._get_rounded_base_and_tax_lines()
        return base_lines

    # Submission

    def _myinvois_submit_documents(self, submissions_content):
        """
        Contact our IAP service in order to send the current document's xml to the MyInvois API.
        Only records in self having a xml_file_content in xml_contents will be sent.

        Please mind that the logic will commit for each batch being sent to the platform.

        :param submissions_content: A dict of the format {record: {'name': '', 'xml': ''}}
        :return: a dict of potential errors in the format {record: errors_list}
        """
        def _format_error_messages(errors_list):
            AccountMoveSend = self.env['account.move.send']
            error_data = {
                'error_title': self.env._("Error when sending the documents to the E-invoicing service."),
                'errors': errors_list,
            }
            return {
                'html_error': AccountMoveSend._format_error_html(error_data),
                'plain_text_error': AccountMoveSend._format_error_text(error_data),
            }

        records_to_send = self.filtered(lambda record: record in submissions_content)
        if not records_to_send:
            return None

        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env['res.company']._with_locked_records(records_to_send)

        error_messages = {}
        success_messages = {}
        invoice_to_cancel = self.env['account.move']

        # We will group per proxy_user, then batch the records in batches of SUBMISSION_MAX_SIZE
        records_per_proxy_users = records_to_send.grouped(lambda r: r._myinvois_get_proxy_user())

        # MyInvois only supports up to 100 document per submission. To avoid timing out on big batches, we split it client side.
        for proxy_user, records_to_send in records_per_proxy_users.items():
            for batch in split_every(SUBMISSION_MAX_SIZE, records_to_send.ids, self.env['myinvois.document'].browse):
                batch_result = proxy_user._l10n_my_edi_contact_proxy(
                    endpoint='api/l10n_my_edi/1/submit_invoices',
                    params={
                        'documents': [{
                            'move_id': record.id,
                            'move_name': submissions_content[record]['name'],
                            'error_document_hash': record.myinvois_error_document_hash,
                            'retry_at': record.myinvois_retry_at,
                            'data': base64.b64encode(submissions_content[record]['xml'].encode()).decode(),
                        } for record in batch],
                    },
                )
                # If an error is present in the result itself (and not per document), it means that the whole submission failed.
                # We don't add to the result but instead directly in the errors.
                if 'error' in batch_result:
                    error_string = self._myinvois_map_error(batch_result['error'])
                    error_messages.update({record.id: _format_error_messages([error_string]) for record in batch})
                else:
                    records_per_id = batch.grouped('id')
                    for document_result in batch_result['documents']:
                        record = records_per_id[document_result['move_id']]
                        success = document_result['success']

                        updated_values = {
                            'myinvois_external_uuid': document_result.get('uuid'),  # rejected documents do not have an uuid.
                            'myinvois_submission_uid': batch_result['submission_uid'],
                            'myinvois_state': 'in_progress' if success else 'invalid',
                        }

                        if success:
                            # Ids are logged for future references. An invalid document may be reset to resend it after correction, which would be a new submission/uuid.
                            success_messages[record.id] = self.env._('The document has been sent to MyInvois with uuid "%(uuid)s" and submission id "%(submission_id)s".\nValidation results will be available shortly.',
                                                                     uuid=document_result['uuid'], submission_id=batch_result['submission_uid'])
                        else:
                            # When we raise a "hash_resubmitted" error, we don't resend the same hash/retry at and don't want to rewrite.
                            if 'error_document_hash' in document_result:
                                updated_values.update({
                                    'myinvois_error_document_hash': document_result['error_document_hash'],
                                    'myinvois_retry_at': document_result['retry_at'],
                                })
                            error_messages[record.id] = _format_error_messages([self._myinvois_map_error(error) for error in document_result['errors']])
                            if self.invoice_ids:
                                invoice_to_cancel |= self.invoice_ids

                        record.write(updated_values)

                if self._can_commit():
                    self.env.cr.commit()

        if success_messages:
            successful_records = self.browse(list(success_messages.keys()))
            successful_records._myinvois_log_message(
                bodies=success_messages,
            )
        if error_messages:
            unsuccessful_records = self.browse(list(error_messages.keys()))
            unsuccessful_records._myinvois_log_message(
                bodies={rid: msg['html_error'] for rid, msg in error_messages.items()},
            )

        if invoice_to_cancel:
            # Invalid moves should be considered as cancelled; they need to be reset to draft, corrected and sent again.
            invoice_to_cancel._l10n_my_edi_cancel_moves()

        return error_messages

    def _myinvois_get_submission_status(self):
        """
        Fetches the status of the submissions in self.

        :return: A dict of the format: {submission_uid: {'error': '', 'statuses': {record: document_statuses}}}
        """
        def _make_deep_default_dict():
            return defaultdict(_make_deep_default_dict)

        if not self:
            return None

        results = _make_deep_default_dict()
        for proxy_user, records in self.grouped(lambda r: r._myinvois_get_proxy_user()).items():
            if not proxy_user:
                continue

            for submission_uid, submission_records in records.grouped('myinvois_submission_uid').items():
                # Filter the submission records to skip batches that we don't want to fetch yet.
                submission_records.filtered(lambda r: not r.myinvois_retry_at or fields.Datetime.from_string(r.myinvois_retry_at) <= datetime.datetime.now())

                if not submission_uid or not submission_records:
                    continue

                self.env["res.company"]._with_locked_records(submission_records)

                records_per_uuid = submission_records.grouped('myinvois_external_uuid')

                result = proxy_user._l10n_my_edi_contact_proxy(
                    endpoint='api/l10n_my_edi/1/get_submission_statuses',
                    params={
                        'submission_uid': submission_uid,
                        'page': 1,
                    },
                )
                if 'error' in result:
                    results[submission_uid]['error'] = self._myinvois_map_error(result['error'])
                else:
                    # While unlikely, if we end up with too many documents we will start by getting all the info.
                    if result['document_count'] > 100:
                        for page in range(2, (result['document_count'] // 100) + 1):
                            if self._can_commit():  # avoid the sleep in tests.
                                time.sleep(0.3)
                            page_result = proxy_user._l10n_my_edi_contact_proxy(
                                endpoint='api/l10n_my_edi/1/get_submission_statuses',
                                params={
                                    'submission_uid': submission_uid,
                                    'page': page,
                                },
                            )
                            result['statuses'].update(page_result['statuses'])

                    for uuid, status in result['statuses'].items():
                        record = records_per_uuid.get(uuid)
                        if record:
                            results[submission_uid]['statuses'][record] = status

                if self._can_commit():  # avoid the sleep in tests.
                    time.sleep(0.3)
        return results

    def _myinvois_submission_statuses_update(self, with_commit=True):
        """
        Fetches and update the status of a group of documents.

        :param with_commit: If True, we will commit after retrieving the status if we can.
        """
        statuses = self._myinvois_get_submission_status()
        for submission_uid, results in statuses.items():
            records = self.browse(list(results['statuses'].keys()))

            if results['error']:
                message = self.env["account.move.send"]._format_error_html({
                    "error_title": self.env._("The status update failed with the following errors:"),
                    "errors": results['error'],
                })
                records._myinvois_log_message(bodies={document.id: message for document in self})
                if with_commit and self._can_commit():
                    self.env.cr.commit()
                continue

            for record, status in results['statuses'].items():
                # For valid documents, we always want to update the try time; it's pointless to fetch too often.
                if record.myinvois_state == 'valid' or status['status'] == 'valid':
                    record.myinvois_retry_at = fields.Datetime.now() + datetime.timedelta(hours=1)

                # If the status did not change, we do not need to do anything more.
                if record.myinvois_state == status['status']:
                    if with_commit and self._can_commit():
                        self.env.cr.commit()
                    continue

                # Invalid documents may not all have a reason, but we still want to log something.
                # We will have a reason when documents are cancelled/rejected though, and we want to log that too.
                message = None
                if status.get('reason') or status['status'] == 'invalid':
                    if status.get('reason'):
                        message = record.env._('The MyInvois platform returned a "%(status)s" status for this document for reason: %(reason)s', status=status['reason'], reason=status['reason'])
                    else:
                        message = record.env._('The MyInvois platform returned an "%(status)s" status for this document.', status=status['reason'])

                record._myinvois_set_state(status["status"], message)
                record._myinvois_set_validation_fields(status)

            if with_commit and self._can_commit():
                self.env.cr.commit()

    def _validate_taxes(self):
        """ Makes use of account.edi.xml.ubl_myinvois_my to validate the taxes for the records in self."""
        if self.invoice_ids:
            self.env["account.edi.xml.ubl_myinvois_my"]._validate_taxes(self.invoice_ids.invoice_line_ids.tax_ids)

    def _myinvois_generate_xml_file(self):
        """ Generate the xml file representing this record(s) attached to this document. """
        self.ensure_one()
        builder = self.env['account.edi.xml.ubl_myinvois_my']
        # 1. Validate the structure of the taxes
        self._validate_taxes()
        # 2. Export the file data
        vals = {'myinvois_document': self.with_context(lang=self.env.company.partner_id.lang)}
        document_node = builder._get_myinvois_document_node(vals)
        vals['document_node'] = document_node
        # 3. Check for any issue with the data
        errors = [constraint for constraint in builder._export_myinvois_document_constraints(vals).values() if constraint]
        # 4. Generate the xml file
        template = builder._get_document_template(vals)
        nsmap = builder._get_document_nsmap(vals)
        xml_content = dict_to_xml(document_node, nsmap=nsmap, template=template)
        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8'), set(errors)

    def _submit_to_myinvois(self):
        """
        Submit the documents in self to MyInvois.
        This action will re-generate a new XML file, in order to ensure that we always send an up-to-date version.
        """
        # Make sure that all documents in self have a file ready to be sent.
        self.action_generate_xml_file()

        # Submit the documents to the API
        errors = self._myinvois_submit_documents({
            document: {
                'name': document.name,
                'xml': base64.b64decode(document.myinvois_file).decode('utf-8'),
            } for document in self
        })

        # When sending an individual document, we can raise once we are sure we logged the errors.
        if len(self) == 1 and errors:
            if self._can_commit():
                self.env.cr.commit()  # Save the error logged in the chatter.
            raise UserError(errors[self.id]['plain_text_error'])

        # Try and get the status, up to three time, stopping if all documents have a status already.
        for _i in range(3):
            self._myinvois_submission_statuses_update()
            if not any(document.myinvois_state == 'in_progress' for document in self):
                break
            if self._can_commit():  # avoid the sleep in tests.
                time.sleep(1)

    # Status Update

    def _myinvois_check_can_update_status(self):
        """ The document status can only be updated (for rejection, or cancellation) up to 72h after the validation time.
        After that, any update will be rejected by the platform, as you are expected to issue a debit/credit note.

        This helper will raise if the status cannot be updated.
        """
        self.ensure_one()
        if not self.myinvois_validation_time:
            return

        time_difference = datetime.datetime.now() - self.myinvois_validation_time
        if time_difference >= datetime.timedelta(days=3):
            raise UserError(self.env._('It has been more than 72h since the document validation, you can no longer cancel it.\n'
                                       'Instead, you should issue a debit or credit note.'))
        if self.myinvois_state not in ['valid', 'rejected']:
            raise UserError(self.env._('You can only change the state of a document in the valid or rejected states.'))

    def _action_myinvois_update_document(self, new_status='cancelled'):
        """
        Returns the action to open the status updated wizard for the mode passed in params.

        Valid values for new status are 'cancelled' and 'rejected'.
        """
        self._myinvois_check_can_update_status()
        return {
            "name": self.env._("Cancel Document"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "myinvois.document.status.update.wizard",
            "target": "new",
            "context": {
                "default_document_id": self.id,
                "default_new_status": new_status,
            },
        }

    def _myinvois_update_document(self, status, reason):
        """
        This method will try to update the status of a document on the platform, and if needed also the status in Odoo.

        There is no "Rejected" status on the platform. The document stays as 'valid' until action is taken by the vendor.
        At that point, the invoice will be cancelled if need be by the call to _myinvois_set_state.
        """
        self.ensure_one()
        self.env['res.company']._with_locked_records(self)
        proxy_user = self._myinvois_get_proxy_user()

        # While we do this check before opening the wizard (to avoid filling the wizard for nothing), it is safer to
        # recheck here in case we exceeded the limit in the meantime or if this is called from elsewhere.
        self._myinvois_check_can_update_status()

        successfully_updated_documents = self.env['myinvois.document']
        for document in self:
            result = proxy_user._l10n_my_edi_contact_proxy(
                endpoint='api/l10n_my_edi/1/update_status',
                params={
                    'status_values': {
                        'uuid': document.myinvois_external_uuid,
                        'reason': reason,
                        'status': status,
                    },
                },
            )

            # If it is not a success, it will have raised an error.
            if 'error' in result:
                document._myinvois_log_message(message=self._myinvois_map_error(result['error']))
            else:
                successfully_updated_documents |= document

        if status in self._fields['myinvois_state'].get_values(self.env):
            successfully_updated_documents._myinvois_set_state(
                state=status,
                message=self.env._('This document has been %(status)s for reason: %(reason)s', status=status, reason=reason),
            )

        if self._can_commit():
            self.env.cr.commit()

    def _myinvois_set_state(self, state, message=None):
        """
        Helper to call when the state of one or more documents change.
        It will handle logging a message if needed, updating the state, cancelling the move when required, and update
        essential fields that should not be forgotten.
        """
        if message:
            self._myinvois_log_message(message)

        self.myinvois_state = state

        # Once invalid, an invoice is not acceptable by the platform.
        # An invalid invoice will never be visible by a customer and should, from my understanding, be considered void.
        # In Odoo, the best way to represent that is by cancelling the invoice.
        if state in CANCELLED_STATES and self.invoice_ids:
            self.invoice_ids._l10n_my_edi_cancel_moves()

    def _myinvois_set_validation_fields(self, validation_result):
        self.ensure_one()
        if self.myinvois_state != 'valid':
            return

        # We receive a timezone_aware datetime, but it should always be in UTC.
        # Odoo expect a timezone unaware datetime in UTC, so we can safely remove the info without any more work needed.
        utc_tz_aware_datetime = dateutil.parser.isoparse(validation_result['valid_datetime'])
        self.write({
            'myinvois_validation_time': utc_tz_aware_datetime.replace(tzinfo=None),
            'myinvois_document_long_id': validation_result['long_id'],
        })

    def _myinvois_single_status_update(self):
        """
        Fetches and update the status of a single document.
        More efficient than using the submission status endpoint.
        """
        self.ensure_one()
        proxy_user = self._myinvois_get_proxy_user()

        self.env['res.company']._with_locked_records(self)

        result = proxy_user._l10n_my_edi_contact_proxy(
            endpoint='api/l10n_my_edi/1/get_status',
            params={
                'document_uuid': self.myinvois_external_uuid,
            },
        )

        if 'error' in result:
            raise UserError(self._myinvois_map_error(result['error']))

        if result['status'] == self.myinvois_state:
            return

        message = None
        if 'validation_errors' in result:
            message = self.env['account.move.send']._format_error_html({
                'error_title': self.env._('The validation failed with the following errors:'),
                'errors': result['validation_errors'],
            })
        elif result.get('status_reason'):
            message = self.env._('This document has been %(status)s for reason: %(reason)s', status=result['status'], reason=result['status_reason'])

        self._myinvois_set_state(result['status'], message)
        self._myinvois_set_validation_fields(result)

    @api.model
    def _myinvois_statuses_update_cron(self):
        """
        This cron is based on the recommended method to fetch the status of the documents according to their doc.
        MAX_SUBMISSION_UPDATE defines how many submissions to process in a single cron run.
        """
        # First step is to get the documents for which the status is not yet final.
        # A document whose status will not change anymore is: (cancelled or invalid) or has been validated more than 74h ago.
        # /!\ when a document validation is pending, myinvois_validation_time is still None. These also need to be updated.
        datetime_threshold = datetime.datetime.now() - datetime.timedelta(hours=74)
        # We always want to fetch in_progress document, it's very likely that their status is already there.
        domain = Domain('myinvois_state', 'in', ('in_progress', False))
        # For valid document, we want them if their myinvois_validation_time is less than 74h ago, and if their myinvois_retry_at in the past.
        domain |= Domain([
            ('myinvois_state', '=', 'valid'),
            ('myinvois_validation_time', '>', datetime_threshold),
            '|',
            ('myinvois_retry_at', '<=', datetime.datetime.now()),
            ('myinvois_retry_at', '=', False),
        ])
        grouped_documents = self.env['myinvois.document']._read_group(
            domain,
            groupby=['myinvois_submission_uid'],
            aggregates=['id:recordset'],
            limit=MAX_SUBMISSION_UPDATE,
        )
        document_count = self.search_count(domain)  # Count the total amount of documents to process.

        processed_documents = 0
        for index, (submission_uid, documents) in enumerate(grouped_documents):
            # Update the status for that one submission. In case of errors, we log it and continue.
            # Errors are quite unlikely in this flow.
            documents._myinvois_submission_statuses_update(with_commit=False)  # We handle the commit after notifying of progress.

            processed_documents += len(documents)
            # Commit if we can, in case an issue arises later.
            if self._can_commit():
                self.env['ir.cron']._commit_progress(processed=processed_documents, remaining=document_count - processed_documents)

                # Avoid sleeping on the last loop and in tests (due to the commit check)
                if index != (len(grouped_documents) - 1):
                    time.sleep(0.3)  # There is a limit of how many calls we can do, so we spread them out a bit.
        if self._can_commit():
            self.env['ir.cron']._commit_progress(processed=processed_documents, remaining=document_count - processed_documents)
