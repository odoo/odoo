# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime, timedelta
from json import dumps
from pprint import pformat

from odoo import models, fields, _, registry, api, SUPERUSER_ID
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import float_round, DEFAULT_SERVER_DATETIME_FORMAT, json_float_round

logger = logging.getLogger(__name__)

IAP_SERVICE_NAME = 'l10n_br_avatax_proxy'
DEFAULT_IAP_ENDPOINT = 'https://l10n-br-avatax.api.odoo.com'
DEFAULT_IAP_TEST_ENDPOINT = 'https://l10n-br-avatax.test.odoo.com'
ICP_LOG_NAME = 'l10n_br_avatax.log.end.date'
AVATAX_PRECISION_DIGITS = 2  # defined by API


class AccountExternalTaxMixinL10nBR(models.AbstractModel):
    _inherit = 'account.external.tax.mixin'

    def _l10n_br_is_avatax(self):
        self.ensure_one()
        return self.country_code == 'BR' and self.fiscal_position_id.l10n_br_is_avatax

    def _compute_is_tax_computed_externally(self):
        super()._compute_is_tax_computed_externally()
        self.filtered(lambda record: record._l10n_br_is_avatax()).is_tax_computed_externally = True

    def _l10n_br_avatax_log(self):
        self.env['account.external.tax.mixin']._enable_external_tax_logging(ICP_LOG_NAME)
        return True

    def _l10n_br_get_date_avatax(self):
        """ Returns the transaction date for this record. """
        raise NotImplementedError()

    def _l10n_br_get_avatax_lines(self):
        """ Returns line dicts for this record created with _l10n_br_build_avatax_line(). """
        raise NotImplementedError()

    def _l10n_br_get_operation_type(self):
        """ Returns the operationType to be used for requests to Avatax. By default, it's "standardSales", but
        can be overriden. """
        return 'standardSales'

    def _l10n_br_get_invoice_refs(self):
        """ Should return a dict of invoiceRefs, as specified by the Avatax API. These are required for
        credit and debit notes. """
        return {}

    def _l10n_br_line_model_name(self):
        return self._name + '.line'

    def _l10n_br_avatax_handle_response(self, response, title):
        if response.get('error'):
            logger.warning(pformat(response), stack_info=True)

            inner_errors = []
            for error in response['error'].get('innerError', []):
                # Useful inner errors are line-specific. Ones that aren't are typically not useful for the user.
                if 'lineCode' not in error:
                    continue

                product_name = self.env[self._l10n_br_line_model_name()].browse(error['lineCode']).product_id.display_name

                inner_errors.append(_('What:'))
                inner_errors.append('- %s: %s' % (product_name, error['message']))

                where = error.get('where', {})
                if where:
                    inner_errors.append(_('Where:'))
                for where_key, where_value in sorted(where.items()):
                    if where_key == 'date':
                        continue
                    inner_errors.append('- %s: %s' % (where_key, where_value))

            return '%s\n%s\n%s' % (title, response['error']['message'], '\n'.join(inner_errors))

    def _l10n_br_avatax_allow_services(self):
        """ Override to allow services. """
        return False

    def _l10n_br_avatax_validate_lines(self, lines):
        """ Avoids doing requests to Avatax that are guaranteed to fail. """
        errors = []
        for line in lines:
            product = line['tempProduct']
            if not product:
                errors.append(_('- A product is required on each line when using Avatax.'))
            elif not self._l10n_br_avatax_allow_services() and product.type == 'service':
                errors.append(_('- Install the "Brazilian Accounting EDI for services" app to electronically invoice services.'))
            elif not product.l10n_br_ncm_code_id:
                errors.append(_('- Please configure a Mercosul NCM Code on %s.', product.display_name))
            elif line['lineAmount'] < 0:
                errors.append(_("- Avatax Brazil doesn't support negative lines."))

        if errors:
            raise ValidationError('\n'.join(errors))

    def _l10n_br_build_avatax_line(self, product, qty, unit_price, total, discount, line_id):
        """ Prepares the line data for the /calculations API call. temp* values are here to help with post-processing
        and will be removed before sending by _remove_temp_values_lines.

        :param product.product product: product on the line
        :param float qty: the number of items on the line
        :param float unit_price: the unit_price on the line
        :param float total: the amount on the line without taxes or discount
        :param float discount: the discount amount on the line
        :param int line_id: the database ID of the line record, this is used to uniquely identify it in Avatax
        :return dict: the basis for the 'lines' value in the /calculations API call
        """
        return {
            'lineCode': line_id,
            'useType': product.l10n_br_use_type,
            'otherCostAmount': 0,
            'freightAmount': 0,
            'insuranceAmount': 0,
            'lineTaxedDiscount': discount,
            'lineAmount': total,
            'lineUnitPrice': unit_price,
            'numberOfItems': qty,
            'itemDescriptor': {
                'description': product.display_name or '',
                'cest': product.l10n_br_cest_code or '',
                # The periods in the code work during tax calculation, but not EDI. Removing them works in both.
                'hsCode': (product.l10n_br_ncm_code_id.code or '').replace('.', ''),
                'source': product.l10n_br_source_origin or '',
                'productType': product.l10n_br_sped_type or '',
            },
            'tempTransportCostType': product.l10n_br_transport_cost_type,
            'tempProduct': product,
        }

    def _l10n_br_distribute_transport_cost_over_lines(self, lines, transport_cost_type):
        """ Avatax requires transport costs to be specified per line. This distributes transport costs (indicated by
        their product's l10n_br_transport_cost_type) over the lines in proportion to their subtotals. """
        type_to_api_field = {
            'freight': 'freightAmount',
            'insurance': 'insuranceAmount',
            'other': 'otherCostAmount',
        }
        api_field = type_to_api_field[transport_cost_type]

        transport_lines = [line for line in lines if line['tempTransportCostType'] == transport_cost_type]
        regular_lines = [line for line in lines if not line['tempTransportCostType']]
        total = sum(line['lineAmount'] for line in regular_lines)

        if not regular_lines:
            raise UserError(_('Avatax requires at least one non-transport line.'))

        for transport_line in transport_lines:
            transport_net = transport_line['lineAmount'] - transport_line['lineTaxedDiscount']
            remaining = transport_net
            for line in regular_lines[:-1]:
                current_cost = float_round(
                    transport_net * (line['lineAmount'] / total),
                    precision_digits=AVATAX_PRECISION_DIGITS
                )
                remaining -= current_cost
                line[api_field] += current_cost

            # put remainder on last line to avoid rounding issues
            regular_lines[-1][api_field] += remaining

        return [line for line in lines if line['tempTransportCostType'] != transport_cost_type]

    def _l10n_br_remove_temp_values_lines(self, lines):
        for line in lines:
            del line['tempTransportCostType']
            del line['tempProduct']

    def _l10n_br_repr_amounts(self, lines):
        """ Ensures all amount fields have the right amount of decimals before sending it to the API. """
        for line in lines:
            for amount_field in ('lineAmount', 'freightAmount', 'insuranceAmount', 'otherCostAmount'):
                line[amount_field] = json_float_round(line[amount_field], AVATAX_PRECISION_DIGITS)

    def _l10n_br_call_avatax_taxes(self):
        """Query Avatax with all the transactions linked to `self`.

        :return (dict<Model, dict>): a mapping between document records and the response from Avatax
        """
        if not self:
            return {}

        company_sudo = self.company_id.sudo()
        api_id, api_key = company_sudo.l10n_br_avatax_api_identifier, company_sudo.l10n_br_avatax_api_key
        if not api_id or not api_key:
            raise RedirectWarning(
                _('Please create an Avatax account'),
                self.env.ref('base_setup.action_general_configuration').id,
                _('Go to the configuration panel'),
            )

        transactions = {record: record._l10n_br_get_calculate_payload() for record in self}
        return {
            record: record._l10n_br_iap_calculate_tax(transaction)
            for record, transaction in transactions.items()
        }

    def _l10n_br_get_partner_type(self, partner):
        if partner.country_code not in ('BR', False):
            return 'foreign'
        elif partner.is_company:
            return 'business'
        else:
            return 'individual'

    def _l10n_br_get_calculate_payload(self):
        """ Returns the full payload containing one record to be used in a /transactions API call. """
        self.ensure_one()
        transaction_date = self._get_date_for_external_taxes()
        partner = self.partner_id
        company = self.company_id.partner_id

        lines = [
            self._l10n_br_build_avatax_line(
                line['product_id'],
                line['qty'],
                line['price_unit'],
                line['qty'] * line['price_unit'],
                line['qty'] * line['price_unit'] * (line['discount'] / 100.0),
                line['id'],
            )
            for line
            in self._get_line_data_for_external_taxes()
        ]
        lines = self._l10n_br_distribute_transport_cost_over_lines(lines, 'freight')
        lines = self._l10n_br_distribute_transport_cost_over_lines(lines, 'insurance')
        lines = self._l10n_br_distribute_transport_cost_over_lines(lines, 'other')

        self._l10n_br_avatax_validate_lines(lines)
        self._l10n_br_remove_temp_values_lines(lines)
        self._l10n_br_repr_amounts(lines)

        simplifiedTaxesSettings = {}
        if company.l10n_br_tax_regime == 'simplified':
            simplifiedTaxesSettings = {'pCredSN': self.company_id.l10n_br_icms_rate}

        return {
            'header': {
                'transactionDate': (transaction_date or fields.Date.today()).isoformat(),
                'amountCalcType': 'gross',
                'documentCode': '%s_%s' % (self._name, self.id),
                'messageType': 'goods',
                'companyLocation': '',
                'operationType': self._l10n_br_get_operation_type(),
                **self._l10n_br_get_invoice_refs(),
                'locations': {
                    'entity': {  # the customer
                        'type': self._l10n_br_get_partner_type(partner),
                        'activitySector': {
                            'code': partner.l10n_br_activity_sector,
                        },
                        'taxesSettings': {
                            'icmsTaxPayer': partner.l10n_br_taxpayer == "icms",
                        },
                        'taxRegime': partner.l10n_br_tax_regime,
                        'address': {
                            'zipcode': partner.zip,
                        },
                        'federalTaxId': partner.vat,
                        'suframa': partner.l10n_br_isuf_code or '',
                    },
                    'establishment': {  # the seller
                        'type': 'business',
                        'activitySector': {
                            'code': company.l10n_br_activity_sector,
                        },
                        'taxesSettings': {
                            'icmsTaxPayer': company.l10n_br_taxpayer == "icms",
                            **simplifiedTaxesSettings,
                        },
                        'taxRegime': company.l10n_br_tax_regime,
                        'address': {
                            'zipcode': company.zip,
                        },
                        'federalTaxId': company.vat,
                        'suframa': company.l10n_br_isuf_code or '',
                    },
                },
            },
            'lines': lines,
        }

    def _l10n_br_get_line_total(self, line_result):
        """To be overridden for non-goods APIs."""
        return line_result["lineNetFigure"] - line_result["lineTaxedDiscount"]

    def _get_external_taxes(self):
        """ Override. """
        details, summary = super()._get_external_taxes()

        def find_or_create_tax(doc, tax_name, price_include):
            def repartition_line(repartition_type):
                return (0, 0, {
                    'repartition_type': repartition_type,
                    'company_id': doc.company_id.id,
                })

            key = (tax_name, price_include, doc.company_id)
            if key not in tax_cache:
                # It's possible for multiple taxes to have the needed l10n_br_avatax_code. E.g.:
                # - existing customer install l10n_br_avatax
                # - computes taxes without reloading the fiscal localization, this creates fallback taxes
                # - reloads the fiscal localization
                # In this case take the most recent tax (the one included in the fiscal localization), that one is
                # most likely the one the user wants and will have the right accounts and tags.
                tax_cache[key] = self.env['account.tax'].with_context(active_test=False).search([
                    ('l10n_br_avatax_code', '=', tax_name),
                    ('price_include', '=', price_include),
                    ('company_id', '=', doc.company_id.id)
                ], limit=1, order='create_date desc')

                # all these taxes are archived by default, unarchive when used
                tax_cache[key].active = True

                if not tax_cache[key]:  # fall back on creating a bare-bones tax
                    tax_cache[key] = self.env['account.tax'].sudo().with_company(doc.company_id).create({
                        'name': tax_name,
                        'l10n_br_avatax_code': tax_name,
                        'amount': 1,  # leaving it at the default 0 causes accounting to ignore these
                        'amount_type': 'percent',
                        'price_include': price_include,
                        'refund_repartition_line_ids': [
                            repartition_line('base'),
                            repartition_line('tax'),
                        ],
                        'invoice_repartition_line_ids': [
                            repartition_line('base'),
                            repartition_line('tax'),
                        ],
                    })

            return tax_cache[key]
        tax_cache = {}

        br_records = self.filtered(lambda record: record._l10n_br_is_avatax())
        for record in br_records:
            if record.currency_id.name != 'BRL':
                raise UserError(_('%s has to use Brazilian Real to calculate taxes with Avatax.', record.display_name))

        query_results = br_records._l10n_br_call_avatax_taxes()
        errors = []
        for document, query_result in query_results.items():
            error = self._l10n_br_avatax_handle_response(query_result, _(
                'Odoo could not fetch the taxes related to %(document)s.',
                document=document.display_name,
            ))
            if error:
                errors.append(error)
        if errors:
            raise UserError('\n\n'.join(errors))

        for document, query_result in query_results.items():
            subtracted_tax_types = set()
            tax_type_to_price_include = {}
            is_return = document._l10n_br_get_operation_type() == 'salesReturn'
            for line_result in query_result['lines']:
                record_id = line_result['lineCode']
                record = self.env[self._l10n_br_line_model_name()].browse(int(record_id))
                details[record] = {}
                details[record]['total'] = self._l10n_br_get_line_total(line_result)
                details[record]['tax_amount'] = 0
                details[record]['tax_ids'] = self.env['account.tax']
                for detail in line_result['taxDetails']:
                    if detail['taxImpact']['impactOnNetAmount'] != 'Informative':
                        tax_amount = detail['tax']
                        if is_return:
                            tax_amount = -tax_amount

                        if detail['taxImpact']['impactOnNetAmount'] == 'Subtracted':
                            tax_amount = -tax_amount
                            subtracted_tax_types.add(detail['taxType'])

                        price_include = detail['taxImpact']['impactOnNetAmount'] == 'Included'

                        # In the unlikely event there is an included and excluded tax with the same tax type we take
                        # whichever comes first. The tax computation will still be correct and the taxByType summary
                        # later will group them together.
                        tax_type_to_price_include.setdefault(detail['taxType'], price_include)
                        tax = find_or_create_tax(document, detail['taxType'], price_include)

                        details[record]['tax_amount'] += tax_amount
                        details[record]['tax_ids'] += tax

            summary[document] = {}
            for tax_type, type_details in query_result['summary']['taxByType'].items():
                tax = find_or_create_tax(document, tax_type, tax_type_to_price_include.get(tax_type, False))

                amount = type_details['tax']
                if is_return:
                    amount = -amount

                if tax_type in subtracted_tax_types:
                    amount = -amount

                # Tax avatax returns is opposite from aml balance (avatax is positive on invoice, negative on refund)
                summary[document][tax] = -amount

        details = {record: taxes for record, taxes in details.items() if taxes['tax_ids']}

        return details, summary

    # IAP related methods
    def _l10n_br_iap_request(self, route, json=None, company=None):
        company = company or self.company_id
        avatax_api_id, avatax_api_key = company.sudo().l10n_br_avatax_api_identifier, company.sudo().l10n_br_avatax_api_key

        default_endpoint = DEFAULT_IAP_ENDPOINT if company.l10n_br_avalara_environment == 'production' else DEFAULT_IAP_TEST_ENDPOINT
        iap_endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_br_avatax_iap.endpoint', default_endpoint)
        environment = company.l10n_br_avalara_environment
        url = f'{iap_endpoint}/api/l10n_br_avatax/1/{route}'

        params = {
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'account_token': self.env['iap.account'].get(IAP_SERVICE_NAME).account_token,
            'avatax': {
                'is_production': environment and environment == 'production',
                'json': json or {},
            }
        }

        if avatax_api_id:
            params['api_id'] = avatax_api_id
            params['api_secret'] = avatax_api_key

        start = str(datetime.utcnow())
        response = iap_jsonrpc(url, params=params, timeout=60)  # longer timeout because create_account can take some time
        end = str(datetime.utcnow())

        # Avatax support requested that requests and responses be provided in JSON, so they can easily load them in their
        # internal tools for troubleshooting.
        self._log_external_tax_request(
            'Avatax Brazil',
            ICP_LOG_NAME,
            f"start={start}\n"
            f"end={end}\n"
            f"args={pformat(url)}\n"
            f"request={dumps(json, indent=2)}\n"
            f"response={dumps(response, indent=2)}"
        )

        return response

    def _l10n_br_iap_ping(self, company):
        # This takes company because this function is called directly from res.config.settings instead of a sale.order or account.move
        return self._l10n_br_iap_request('ping', company=company)

    def _l10n_br_iap_create_account(self, account_data, company):
        # This takes company because this function is called directly from res.config.settings instead of a sale.order or account.move
        return self._l10n_br_iap_request('create_account', account_data, company=company)

    def _l10n_br_iap_calculate_tax(self, transaction):
        return self._l10n_br_iap_request('calculate_tax', transaction)
