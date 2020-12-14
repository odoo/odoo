# -*- coding: utf-8 -*-

from odoo import models, fields, _, release
from odoo.exceptions import ValidationError
import requests
from requests.exceptions import ConnectTimeout
import uuid

COUNTRY_CODE_MAP = {
    "BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU",
    "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA",
    "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA",
    "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM",
    "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF",
    "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB",
    "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND",
    "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ",
    "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM",
    "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB",
    "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG",
    "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL",
    "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT",
    "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN",
    "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM",
    "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU",
    "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK",
    "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW",
    "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR",
    "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK",
    "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE",
    "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA",
    "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN",
    "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR",
    "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT",
    "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM",
    "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND",
    "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"
}


class PosSession(models.Model):
    _inherit = 'pos.session'
    fiskaly_cash_point_closing_uuid = fields.Char(readonly=True)

    def _finalize_validation(self, orders):
        if self.config_id.is_company_country_germany:
            if len(orders) > 0:
                orders = orders.sorted('fiskaly_time_end')
                try:
                    headers = self.fiskaly_authentication()
                    json_payload = self._create_cash_point_closing_json(orders, headers)
                    self.send_fiskaly_cash_point_closing(json_payload, headers)
                except ConnectionError:
                    raise ValidationError(_("Connection error between Odoo and Fiskaly."))
                except ConnectTimeout:
                    raise ValidationError(_("There are some connection issues between us and Fiskaly, try again later."))

        return super(PosSession, self)._finalize_validation(orders)

    def _create_cash_point_closing_json(self, orders, headers):
        vat_definitions = self.fiskaly_get_vat_definitions(headers)
        cash_statement = self._init_cash_statement()
        transaction_list = []
        business_cases_vat_statement = {}
        cash_amount_currency = 0
        payment_type_cash_statement_amount = 0
        payment_type_cashless_statement_amount = 0

        for order in orders:
            cash_statement['payment']['full_amount'] += round(order.amount_total, 2)
            payment_type_cash_amount = 0
            payment_type_cashless_amount = 0
            for payment in order.payment_ids:
                amount = round(payment.amount)
                if payment.payment_method_id.is_cash_count:
                    cash_statement['payment']['cash_amount'] += amount
                    cash_amount_currency += amount
                    payment_type_cash_statement_amount += amount
                    payment_type_cash_amount += amount
                else:
                    payment_type_cashless_statement_amount += amount
                    payment_type_cashless_amount += amount

            payment_types = self._create_transaction_payment_types(payment_type_cash_amount,
                                                                   payment_type_cashless_amount)
            transaction = self._create_transaction(order, vat_definitions, payment_types, business_cases_vat_statement)
            transaction_list.append(transaction)

        for amount_vat_id_value in business_cases_vat_statement.values():
            cash_statement['business_cases'][0]['amounts_per_vat_id'].append(amount_vat_id_value)
        if cash_amount_currency:
            cash_statement['payment']['cash_amounts_by_currency'].append({'currency_code': 'EUR',
                                                                          'amount': cash_amount_currency})
        if payment_type_cash_statement_amount:
            cash_statement['payment']['payment_types'].append({'type': 'Bar', 'currency_code': 'EUR',
                                                               'amount': payment_type_cash_statement_amount})
        if payment_type_cashless_statement_amount:
            cash_statement['payment']['payment_types'].append({'type': 'Unbar', 'currency_code': 'EUR',
                                                               'amount': payment_type_cashless_statement_amount})

        json = {
            'client_id': self.config_id.fiskaly_client_id,
            'cash_point_closing_export_id': str(self.id),
            'head': {
                'export_creation_date': fields.Datetime.now().timestamp(),
                'first_transaction_export_id': str(orders[0].id),
                'last_transaction_export_id': str(orders[-1].id)
            },
            'cash_statement': cash_statement,
            'transactions': transaction_list
        }

        return json

    def send_fiskaly_cash_point_closing(self, json_payload, headers):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_dsfinvk_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))
        cash_point_closing_uuid = str(uuid.uuid4())
        cash_point_closing_resp = requests.put('{0}cash_point_closings/{1}'.format(url, cash_point_closing_uuid),
                                               headers=headers, timeout=timeout, json=json_payload)
        if cash_point_closing_resp.status_code == 404:  # register the cash register
            self.create_fiskaly_cash_register(headers)
            cash_point_closing_resp = requests.put('{0}cash_point_closings/{1}'.format(url, cash_point_closing_uuid),
                                                   headers=headers, timeout=timeout, json=json_payload)
        if cash_point_closing_resp.status_code == 200:
            self.write({'fiskaly_cash_point_closing_uuid': cash_point_closing_uuid})
        else:
            raise ValidationError(_("There is an unknown error happening with Fiskaly, please try again later or " \
                                    "contact the support."))

    def fiskaly_authentication(self):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_dsfinvk_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))

        auth_response = requests.post(url + 'auth', json={
            'api_secret': self.company_id.fiskaly_secret,
            'api_key': self.company_id.fiskaly_key
        }, timeout=timeout)
        if auth_response.status_code == 401:  # Todo to remove later
            raise ValidationError(_("The combination of your Fiskaly API key and secret is incorrect. " \
                                    "Please update them in your company settings"))
        headers = {'Authorization': 'Bearer ' + auth_response.json()['access_token']}
        return headers

    def create_fiskaly_cash_register(self, headers):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_dsfinvk_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))
        payload = {
            'cash_register_type': {
                'type': 'MASTER',
                'tss_id': self.config_id.fiskaly_tss_id
            },
            'brand': 'Odoo',
            'model': 'Odoo',
            'base_currency_code': 'EUR',
            'software': {
                'version': release.version
            }
        }

        requests.put('{0}cash_registers/{1}'.format(url, self.config_id.fiskaly_client_id),
                     headers=headers, timeout=timeout, json=payload)

    def fiskaly_get_vat_definitions(self, headers):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_dsfinvk_api_url')
        vat_definitions_resp = requests.get(url + 'vat_definitions', headers=headers)
        vat_definitions = {}
        for vat in vat_definitions_resp.json()['data']:
            vat_definitions[vat['percentage']] = vat['vat_definition_export_id']

        return vat_definitions

    def _init_cash_statement(self):
        cash_statement = {
            'business_cases': [{
                'type': 'Umsatz',
                'amounts_per_vat_id': []
            }],
            'payment': {
                'full_amount': 0,
                'cash_amount': 0,
                'cash_amounts_by_currency': [],
                'payment_types': []
            }
        }

        return cash_statement

    def _create_transaction_payment_types(self, payment_type_cash_amount, payment_type_cashless_amount):
        payment_types = []
        if payment_type_cash_amount:
            payment_types.append(
                {'type': 'Bar', 'currency_code': 'EUR', 'amount': payment_type_cash_amount})
        if payment_type_cashless_amount:
            payment_types.append(
                {'type': 'Unbar', 'currency_code': 'EUR', 'amount': payment_type_cashless_amount})

        return payment_types

    def _create_transaction_header(self, order):
        header = {
            'tx_id': order.fiskaly_transaction_uuid,
            'transaction_export_id': str(order.id),
            'closing_client_id': order.config_id.fiskaly_client_id,
            'type': 'Beleg',
            'storno': False,
            'number': order.id,
            'timestamp_start': order.fiskaly_time_start.timestamp(),
            'timestamp_end': order.fiskaly_time_end.timestamp(),
            'user': {'user_export_id': str(order.user_id.id), 'name': order.user_id.name},
            'buyer': self._create_transaction_buyer(order)
        }

        return header

    def _create_transaction_buyer(self, order):
        buyer = {}

        if order.partner_id:
            partner = order.partner_id
            buyer['name'] = partner.name
            buyer['buyer_export_id'] = str(partner.id)
            buyer['type'] = 'Kunde' if self.company_id == partner.company_id else 'Mitarbeiter'
            if order.amount_total > 200:
                address = {}
                if partner.street:
                    address['street'] = partner.street
                if partner.zip:
                    address['postal_code'] = partner.zip
                if partner.country_id:
                    address['country_code'] = COUNTRY_CODE_MAP[partner.country_id.code]
                buyer['address'] = address
        else:
            buyer['name'] = 'Customer'
            buyer['buyer_export_id'] = 'null'
            buyer['type'] = 'Kunde'

        return buyer

    def _create_line_data(self, line, vat_definition_id):
        subtotal_incl = round(line.price_subtotal_incl, 2)
        subtotal_excl = round(line.price_subtotal, 2)
        vat_amount = round(subtotal_incl - subtotal_excl, 2)

        line_data = {
            'business_case': {
                'type': 'Umsatz',
                'amounts_per_vat_id': [{
                    'vat_definition_export_id': vat_definition_id,
                    'incl_vat': subtotal_incl,
                    'excl_vat': subtotal_excl,
                    'vat': vat_amount
                }],
            },
            'lineitem_export_id': line.id,
            'storno': False,
            'text': line.full_product_name,
            'item': {
                'number': line.product_id.id,
                'quantity': round(line.qty, 3),
                'price_per_unit': round(subtotal_incl / line.qty, 5)
            }
        }

        return line_data

    def _update_business_cases_vat_statement(self, business_cases_vat_statement, line, vat_definition_id):
        subtotal_incl = round(line.price_subtotal_incl, 2)
        subtotal_excl = round(line.price_subtotal, 2)
        vat_amount = round(subtotal_incl - subtotal_excl, 2)

        if vat_definition_id not in business_cases_vat_statement:
            business_cases_vat_statement[vat_definition_id] = {
                'vat_definition_export_id': vat_definition_id,
                'incl_vat': subtotal_incl,
                'excl_vat': subtotal_excl,
                'vat': vat_amount
            }
        else:
            business_cases_vat_statement[vat_definition_id]['incl_vat'] += subtotal_incl
            business_cases_vat_statement[vat_definition_id]['excl_vat'] += subtotal_excl
            business_cases_vat_statement[vat_definition_id]['vat'] += vat_amount

    def _create_transaction(self, order, vat_definitions, payment_types, business_cases_vat_statement):
        data = {
            'full_amount_incl_vat': round(order.amount_total),
            'payment_types': payment_types,
            'amounts_per_vat_id': [],
            'lines': []
        }

        for line in order.lines:
            vat_definition_id = vat_definitions[line.tax_ids[0].amount]
            data['lines'].append(self._create_line_data(line, vat_definition_id))
            self._update_business_cases_vat_statement(business_cases_vat_statement, line, vat_definition_id)

        transaction = {
            'head': self._create_transaction_header(order),
            'data': data,
            'security': {'tss_tx_id': order.fiskaly_transaction_uuid}
        }

        return transaction
