# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from pprint import pformat

from odoo import models, api, fields, _
from odoo.addons.account_avatax.lib.avatax_client import AvataxClient
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.release import version
from odoo.tools import float_repr, float_round

_logger = logging.getLogger(__name__)


class AccountExternalTaxMixin(models.AbstractModel):
    _inherit = 'account.external.tax.mixin'

    # Technical field used for the visibility of fields and buttons
    is_avatax = fields.Boolean(compute='_compute_is_avatax')

    @api.depends('fiscal_position_id')
    def _compute_is_avatax(self):
        for record in self:
            record.is_avatax = record.fiscal_position_id.is_avatax

    def _compute_is_tax_computed_externally(self):
        super()._compute_is_tax_computed_externally()
        self.filtered('is_avatax').is_tax_computed_externally = True

    def _get_external_taxes(self):
        """ Override. """
        def find_or_create_tax(doc, detail):
            def repartition_line(repartition_type, account=None):
                return (0, 0, {
                    'repartition_type': repartition_type,
                    'tag_ids': [],
                    'company_id': doc.company_id.id,
                    'account_id': account and account.id,
                })
            # 4 precision digits is the same as is used on the amount field of account.tax
            name_precision = 4
            tax_name = '%s [%s] (%s %%)' % (
                detail['taxName'],
                detail['jurisCode'],
                float_repr(float_round(detail['rate'] * 100, name_precision), name_precision),
            )
            key = (tax_name, doc.company_id)
            if key not in tax_cache:
                tax_cache[key] = self.env['account.tax'].search([
                    *self.env['account.tax']._check_company_domain(doc.company_id),
                    ('name', '=', tax_name),
                ]) or self.env['account.tax'].sudo().with_company(doc.company_id).create({
                    'name': tax_name,
                    'amount': detail['rate'] * 100,
                    'amount_type': 'percent',
                    'refund_repartition_line_ids': [
                        repartition_line('base'),
                        repartition_line('tax', doc.fiscal_position_id.avatax_refund_account_id),
                    ],
                    'invoice_repartition_line_ids': [
                        repartition_line('base'),
                        repartition_line('tax', doc.fiscal_position_id.avatax_invoice_account_id),
                    ],
                })
            return tax_cache[key]

        details, summary = super()._get_external_taxes()
        tax_cache = {}

        query_results = self.filtered('is_avatax')._query_avatax_taxes()
        errors = []
        for document, query_result in query_results.items():
            error = self._handle_response(query_result, _(
                'Odoo could not fetch the taxes related to %(document)s.\n'
                'Please check the status of `%(technical)s` in the AvaTax portal.',
                document=document.display_name,
                technical=document.avatax_unique_code,
            ))
            if error:
                errors.append(error)
        if errors:
            raise UserError('\n\n'.join(errors))

        for document, query_result in query_results.items():
            is_return = document._get_avatax_document_type() == 'ReturnInvoice'
            line_amounts_sign = -1 if is_return else 1

            for line_result in query_result['lines']:
                record_id = line_result['lineNumber'].split(',')
                record = self.env[record_id[0]].browse(int(record_id[1]))
                details.setdefault(record, {})
                details[record]['total'] = line_amounts_sign * line_result['lineAmount']
                details[record]['tax_amount'] = line_amounts_sign * line_result['tax']
                for detail in line_result['details']:
                    tax = find_or_create_tax(document, detail)
                    details[record].setdefault('tax_ids', self.env['account.tax'])
                    details[record]['tax_ids'] += tax

            summary[document] = {}
            for summary_line in query_result['summary']:
                tax = find_or_create_tax(document, summary_line)

                # Tax avatax returns is opposite from aml balance (avatax is positive on invoice, negative on refund)
                summary[document][tax] = -summary_line['tax']

        return details, summary


    @api.constrains('partner_id', 'fiscal_position_id')
    def _check_address(self):
        incomplete_partner_to_records = self._get_partners_with_incomplete_information()

        if incomplete_partner_to_records:
            error = _("The following customer(s) need to have a zip, state and country when using Avatax:")
            partner_errors = [
                _("- %s (ID: %s) on %s", partner.display_name, partner.id, ", ".join(record.display_name for record in records))
                for partner, records in incomplete_partner_to_records.items()
            ]
            raise ValidationError(error + "\n" + "\n".join(partner_errors))

    def _get_partners_with_incomplete_information(self, partner=None):
        """
            This getter will return a dict of partner having missing information like country_id, zip or state as the key
            and the move as value
        """
        incomplete_partner_to_records = {}
        for record in self.filtered(lambda r: r._perform_address_validation()):
            partner = partner or record.partner_id
            country = partner.country_id
            if (
                partner != self.env.ref('base.public_partner')
                and (
                    not country
                    or (country.zip_required and not partner.zip)
                    or (country.state_required and not partner.state_id)
                )
            ):
                incomplete_partner_to_records.setdefault(partner, []).append(record)

        return incomplete_partner_to_records

    # #############################################################################################
    # TO IMPLEMENT IN BUSINESS DOCUMENT
    # #############################################################################################

    def _get_avatax_dates(self):
        """Get the dates related to the document.

        :return (tuple<date, date>): the document date and the tax computation date
        """
        raise NotImplementedError()  # implement in business document

    def _get_avatax_document_type(self):
        """Get the Avatax Document Type.

        Specifies the type of document to create. A document type ending with Invoice is a
        permanent transaction that will be recorded in AvaTax. A document type ending with Order is
        a temporary estimate that will not be preserved.

        :return (string): i.e. `SalesInvoice`, `ReturnInvoice` or `SalesOrder`
        """
        raise NotImplementedError()  # implement in business document

    def _get_avatax_ship_to_partner(self):
        """Get the customer's shipping address.

        This assumes that partner_id exists on models using this class.

        :return (Model): a `res.partner` record
        """
        return self.partner_shipping_id or self.partner_id

    def _perform_address_validation(self):
        """Allows to bypass the _check_address constraint.

        :return (bool): whether to execute the _check_address constraint
        """
        return self.fiscal_position_id.is_avatax

    # #############################################################################################
    # HELPERS
    # #############################################################################################

    def _get_avatax_invoice_line(self, line_data):
        """Create a `LineItemModel` based on line_data.

        :param line_data (dict): data returned by _get_line_data_for_external_taxes()
        """
        product = line_data['product_id']
        if not product._get_avatax_category_id():
            raise UserError(_(
                'The Avalara Tax Code is required for %(name)s (#%(id)s)\n'
                'See https://taxcode.avatax.avalara.com/',
                name=product.display_name,
                id=product.id,
            ))
        item_code = product.code or ""
        if self.env.company.avalara_use_upc and product.barcode:
            item_code = f'UPC:{product.barcode}'
        return {
            'amount': -line_data["price_subtotal"] if line_data["is_refund"] else line_data["price_subtotal"],
            'description': product.display_name,
            'quantity': abs(line_data["qty"]),
            'taxCode': product._get_avatax_category_id().code,
            'itemCode': item_code,
            'number': "%s,%s" % (line_data["model_name"], line_data["id"]),
        }

    # #############################################################################################
    # PRIVATE UTILITIES
    # #############################################################################################

    def _get_avatax_ref(self):
        """Get a transaction reference."""
        return self.name or ''

    def _get_avatax_address_from_partner(self, partner):
        """Returns a dict containing the values required for an avatax address
        """
        # Partner contains the partner_shipping_id or the partner_id
        incomplete_partner = self._get_partners_with_incomplete_information(partner)
        if incomplete_partner.get(partner):
            res = {
                'latitude': partner.partner_latitude,
                'longitude': partner.partner_longitude,
            }
        else:
            res = {
                'city': partner.city,
                'country': partner.country_id.code,
                'region': partner.state_id.code,
                'postalCode': partner.zip,
                'line1': partner.street,
            }
        return res

    def _get_avatax_addresses(self, partner):
        """Get the addresses related to a partner.

        :param partner (Model<res.partner>): the partner we need the addresses of.
        :return (dict): the AddressesModel to return to Avatax
        """
        res = {
            'shipFrom': self._get_avatax_address_from_partner(self.company_id.partner_id),
            'shipTo': self._get_avatax_address_from_partner(partner),
        }
        return res

    def _get_avatax_invoice_lines(self):
        return [self._get_avatax_invoice_line(line_data) for line_data in self._get_line_data_for_external_taxes()]

    def _get_avatax_taxes(self, commit):
        """Get the transaction values.

        :return (dict): a mapping defined by the AvataxModel `CreateTransactionModel`.
        """
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        document_date, tax_date = self._get_avatax_dates()
        taxes = {
            'addresses': self._get_avatax_addresses(self._get_avatax_ship_to_partner()),
            'companyCode': self.company_id.partner_id.avalara_partner_code or '',
            'customerCode': partner.avalara_partner_code or partner.avatax_unique_code,
            'entityUseCode': partner.with_company(self.company_id).avalara_exemption_id.code or '',
            'businessIdentificationNo': partner.vat or '',
            'date': (document_date or fields.Date.today()).isoformat(),
            'lines': self._get_avatax_invoice_lines(),
            'type': self._get_avatax_document_type(),
            'code': self.avatax_unique_code,
            'referenceCode': self._get_avatax_ref(),
            'currencyCode': self.currency_id.name or '',
            'commit': commit and self.company_id.avalara_commit,
        }

        if tax_date:
            taxes['taxOverride'] = {
                'type': 'taxDate',
                'reason': 'Manually changed the tax calculation date',
                'taxDate': tax_date.isoformat(),
            }

        return taxes

    def _commit_avatax_taxes(self):
        self._query_avatax_taxes(commit=True)

    def _query_avatax_taxes(self, commit=False):
        """Query Avatax with all the transactions linked to `self`.

        :return (dict<Model, dict>): a mapping between document records and the response from Avatax
        """
        if not self:
            return {}
        if not self.company_id.sudo().avalara_api_id or not self.company_id.sudo().avalara_api_key:
            raise RedirectWarning(
                _('Please add your AvaTax credentials'),
                self.env.ref('base_setup.action_general_configuration').id,
                _("Go to the configuration panel"),
            )
        client = self._get_client(self.company_id)
        transactions = {record: record._get_avatax_taxes(commit) for record in self}
        # TODO batch the `create_transaction`
        return {
            record: client.create_transaction(transaction, include='Lines')
            for record, transaction in transactions.items()
        }

    def _uncommit_external_taxes(self):
        for record in self.filtered('is_avatax'):
            if not record.company_id.avalara_commit:
                continue
            client = self._get_client(record.company_id)
            query_result = client.uncommit_transaction(
                companyCode=record.company_id.partner_id.avalara_partner_code,
                transactionCode=record.avatax_unique_code,
            )
            error = self._handle_response(query_result, _(
                'Odoo could not change the state of the transaction related to %(document)s in'
                ' AvaTax\nPlease check the status of `%(technical)s` in the AvaTax portal.',
                document=record.display_name,
                technical=record.avatax_unique_code,
            ))
            if error:
                raise UserError(error)

        return super()._uncommit_external_taxes()

    def _void_external_taxes(self):
        for record in self.filtered('is_avatax'):
            if not record.company_id.avalara_commit:
                continue
            client = self._get_client(record.company_id)
            query_result = client.void_transaction(
                companyCode=record.company_id.partner_id.avalara_partner_code,
                transactionCode=record.avatax_unique_code,
                model={"code": "DocVoided"},
            )

            # There's nothing to void when a draft record is deleted without ever being sent to Avatax.
            if query_result.get('error', {}).get('code') == 'EntityNotFoundError':
                _logger.info(pformat(query_result))
                continue

            error = self._handle_response(query_result, _(
                'Odoo could not void the transaction related to %(document)s in AvaTax\nPlease '
                'check the status of `%(technical)s` in the AvaTax portal.',
                document=record.display_name,
                technical=record.avatax_unique_code,
            ))
            if error:
                raise UserError(error)

        return super()._void_external_taxes()

    # #############################################################################################
    # COMMUNICATION
    # #############################################################################################

    def _handle_response(self, response, title):
        if response.get('errors'):  # http error
            _logger.warning(pformat(response), stack_info=True)
            return '%s\n%s' % (title, _(
                '%(response)s',
                response=response.get('title', ''),
            ))
        if response.get('error'):  # avatax error
            _logger.warning(pformat(response), stack_info=True)
            messages = '\n'.join(detail['message'] for detail in response['error']['details'])
            return '%s\n%s' % (title, messages)

    def _get_client(self, company):
        client = AvataxClient(
            app_name='Odoo',
            app_version=version,
            environment=company.avalara_environment,
        )
        client.add_credentials(
            company.sudo().avalara_api_id or '',
            company.sudo().avalara_api_key or '',
        )
        client.logger = lambda message: self._log_external_tax_request(
            'Avatax US', 'account_avatax.log.end.date', message
        )
        return client
