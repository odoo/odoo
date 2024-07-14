# -*- coding: utf-8 -*-

from typing import Dict

from odoo import models, fields, _, release
from odoo.tools.float_utils import float_repr
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
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
    l10n_de_fiskaly_cash_point_closing_uuid = fields.Char(string="Fiskaly Cash Point Closing Uuid", readonly=True,
        help="The uuid of the 'cash point closing' created at Fiskaly when closing the session.")

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super()._validate_session(balancing_account, amount_to_balance, bank_payment_method_diffs)

        # If the result is a dict, this means that there was a problem and the _validate_session was not completed.
        # In this case, a wizard should show up which is represented by the returned dictionary.
        # Return the dictionary to prevent running the remaining code.
        if isinstance(res, dict):
            return res
        orders = self.order_ids.filtered(lambda o: o.state in ['done', 'invoiced'])
        # We don't want to block the user that need to validate his session order in order to create his TSS
        if self.config_id.is_company_country_germany and self.config_id.l10n_de_fiskaly_tss_id and orders:
            orders = orders.sorted('l10n_de_fiskaly_time_end')
            json = self._l10n_de_create_cash_point_closing_json(orders)
            self._l10n_de_send_fiskaly_cash_point_closing(json)

        return res

    def _l10n_de_create_cash_point_closing_json(self, orders):
        vat_definitions = self._l10n_de_fiskaly_get_vat_definitions()

        self.env.cr.execute("""
            SELECT pm.is_cash_count, sum(p.amount) AS amount
            FROM pos_payment p
                LEFT JOIN pos_payment_method pm ON p.payment_method_id=pm.id
                JOIN account_journal journal ON pm.journal_id=journal.id
            WHERE p.session_id=%s AND journal.type IN ('cash', 'bank')
            GROUP BY pm.is_cash_count
        """, [self.id])
        total_payment_result = self.env.cr.dictfetchall()

        total_cash = 0
        total_bank = 0
        for payment in total_payment_result:
            if payment['is_cash_count']:
                total_cash = payment['amount']
            else:
                total_bank = payment['amount']

        self.env.cr.execute("""
            SELECT account_tax.amount,
                   sum(pos_order_line.price_subtotal) as excl_vat,
                   sum(pos_order_line.price_subtotal_incl) as incl_vat
            FROM pos_order
            JOIN pos_order_line ON pos_order.id=pos_order_line.order_id
            JOIN account_tax_pos_order_line_rel ON account_tax_pos_order_line_rel.pos_order_line_id=pos_order_line.id
            JOIN account_tax ON account_tax_pos_order_line_rel.account_tax_id=account_tax.id
            WHERE pos_order.session_id=%s
            GROUP BY account_tax.amount
        """, [self.id])

        amounts_per_vat_id_result = self.env.cr.dictfetchall()

        return self._get_dsfinvk_cash_point_closing_data(**{
            'orders': orders,
            'total_cash': total_cash,
            'total_bank': total_bank,
            'vat_definitions': vat_definitions,
            'amounts_per_vat_id': amounts_per_vat_id_result
        })

    def _get_dsfinvk_cash_point_closing_data(
        self,
        orders,
        total_cash,
        total_bank,
        vat_definitions,
        amounts_per_vat_id,
    ) -> Dict:

        company = self.company_id
        config = self.config_id
        session = self

        return {
            "client_id": config.l10n_de_fiskaly_client_id,
            "cash_point_closing_export_id": session.id,
            "head": {
                "export_creation_date": int(session.write_date.timestamp()),
                "first_transaction_export_id": f"{orders[0].id}",
                "last_transaction_export_id": f"{orders[-1].id}",
            },
            "cash_statement": {
                "business_cases": [
                    {
                        "type": "Umsatz",
                        "amounts_per_vat_id": [
                            {
                                "vat_definition_export_id": vat_definitions[a["amount"]],
                                "incl_vat": float_repr(a["incl_vat"], 5),
                                "excl_vat": float_repr(a["excl_vat"], 5),
                                "vat": float_repr(a["incl_vat"] - a["excl_vat"], 5),
                            }
                            for a in amounts_per_vat_id
                        ],
                    }
                ],
                "payment": {
                    "full_amount": float_repr(total_cash + total_bank, 5),
                    "cash_amount": float_repr(total_cash, 5),
                    "cash_amounts_by_currency": [
                        {"currency_code": "EUR", "amount": float_repr(total_cash, 5)}
                    ],
                    "payment_types":
                        ([{"type": "Bar", "currency_code": "EUR", "amount": float_repr(total_cash, 5)}]
                            if total_cash or not total_bank else []) +
                        ([{"type": "Unbar", "currency_code": "EUR", "amount": float_repr(total_bank, 5)}]
                            if total_bank else [])
                }
            },
            "transactions": [
                {
                    "head": {
                        "tx_id": f"{o.l10n_de_fiskaly_transaction_uuid}",
                        "transaction_export_id": f"{o.id}",
                        "closing_client_id": f"{config.l10n_de_fiskaly_client_id}",
                        "type": "Beleg",
                        "storno": False,
                        "number": o.id,
                        "timestamp_start": int(o.l10n_de_fiskaly_time_start.timestamp()),
                        "timestamp_end": int(o.l10n_de_fiskaly_time_end.timestamp()),
                        "user": {"user_export_id": f"{o.user_id.id}", "name": f"{o.user_id.name[:50]}"},
                        "buyer": {
                            "name": f"{o.partner_id.name[:50]}",
                            "buyer_export_id": f"{o.partner_id.id}",
                            "type": "Kunde"
                            if company.id != o.partner_id.company_id.id
                            else "Mitarbeiter",
                            **({
                                    "address": {
                                        **({"street": f"{o.partner_id.street}"} if o.partner_id.street else {}),
                                        **({"postal_code": f"{o.partner_id.zip}"} if o.partner_id.zip else {}),
                                        **({"country_code": f"{COUNTRY_CODE_MAP.get(o.partner_id.country_id.code)}"} if COUNTRY_CODE_MAP.get(o.partner_id.country_id.code) else {}),
                                    }
                                }
                                if o.amount_total > 200
                                else {}
                            ),
                        }
                        if o.partner_id
                        else {"name": "Customer", "buyer_export_id": "null", "type": "Kunde"},
                    },
                    "data": {
                        "full_amount_incl_vat": float_repr(o.amount_total, 5),
                        "payment_types": [
                            {
                                "type": f"{p['type']}",
                                "currency_code": "EUR",
                                "amount": float_repr(p["amount"], 5),
                            }
                            for p in o._l10n_de_payment_types()
                        ],
                        "amounts_per_vat_id": [
                            {
                                "vat_definition_export_id": vat_definitions[a["amount"]],
                                "incl_vat": float_repr(a["incl_vat"], 5),
                                "excl_vat": float_repr(a["excl_vat"], 5),
                                "vat": float_repr(a["incl_vat"] - a["excl_vat"], 5),
                            }
                            for a in o._l10n_de_amounts_per_vat()
                        ],
                        "lines": [
                            {
                                "business_case": {
                                    "type": "Umsatz",
                                    "amounts_per_vat_id": [
                                        {
                                            "vat_definition_export_id": vat_definitions[
                                                l.tax_ids[0].amount
                                            ],
                                            "incl_vat": float_repr(l.price_subtotal_incl, 5),
                                            "excl_vat": float_repr(l.price_subtotal, 5),
                                            "vat": float_repr(
                                                l.price_subtotal_incl - l.price_subtotal, 5
                                            ),
                                        }
                                    ],
                                },
                                "lineitem_export_id": f"{l.id}",
                                "storno": False,
                                "text": f"{l.product_id.product_tmpl_id.name}",
                                "item": {
                                    "number": f"{l.product_id.id}",
                                    "quantity": float_repr(l.qty, 3),
                                    "price_per_unit": float_repr(l.price_unit, 5)
                                    if l.qty == 0
                                    else float_repr(l.price_subtotal_incl / l.qty, 5),
                                },
                            }
                            for l in o.lines
                        ],
                    },
                    "security": {"tss_tx_id": f"{o.l10n_de_fiskaly_transaction_uuid}"},
                }
                for o in orders
            ],
        }

    def _l10n_de_send_fiskaly_cash_point_closing(self, json):
        cash_point_closing_uuid = str(uuid.uuid4())
        cash_register_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('GET', '/cash_registers/%s' % self.config_id.l10n_de_fiskaly_client_id)
        if cash_register_resp.status_code == 404:  # register the cash register
            self._l10n_de_create_fiskaly_cash_register()
        cash_point_closing_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('PUT', '/cash_point_closings/%s' % cash_point_closing_uuid, json)
        if cash_point_closing_resp.status_code != 200:
            raise UserError(_('Cash point closing error with Fiskaly: \n %s', cash_point_closing_resp.json()))
        self.write({'l10n_de_fiskaly_cash_point_closing_uuid': cash_point_closing_uuid})

    def _l10n_de_create_fiskaly_cash_register(self):
        json = {
            'cash_register_type': {
                'type': 'MASTER',
                'tss_id': self.config_id._l10n_de_get_tss_id()
            },
            'brand': 'Odoo',
            'model': 'Odoo',
            'base_currency_code': 'EUR',
            'software': {
                'version': release.version
            }
        }

        self.company_id._l10n_de_fiskaly_dsfinvk_rpc('PUT', '/cash_registers/%s' % self.config_id.l10n_de_fiskaly_client_id, json)

    def _l10n_de_fiskaly_get_vat_definitions(self):
        vat_definitions_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('GET', '/vat_definitions')
        vat_definitions = {}
        for vat in vat_definitions_resp.json()['data']:
            vat_definitions[vat['percentage']] = vat['vat_definition_export_id']

        return vat_definitions
