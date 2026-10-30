# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import time
import uuid
from base64 import b64decode
from binascii import Error as BinasciiError
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

from odoo.exceptions import UserError

from odoo.addons.l10n_cn_edi_yunshui.crypto import sm4_envelope

_logger = logging.getLogger(__name__)

HOSTS = {
    'test': 'https://llys.51fapiao.cn/openapi',
    'prod': 'https://ll.51fapiao.cn/openapi',
}
TIMEOUT = 30

SIMPLE_ISSUE = 'ele.encrypt.simpleInvoiceIssue'
QUERY_RESULT = 'ele.encrypt.queryResult'
LOGIN = 'ele.eleLogin'
GET_CREDIT_LINE = 'ele.creditLine'
DOWNLOAD_INVOICE = 'ele.invoice.download'
QUERY_RED_FORM = 'ele.hzqrd.query'

INVOICE_KIND = {'01': '81', '02': '82'}
RED_REASONS = {'01': '01', '02': '02', '03': '03', '04': '04'}
PENDING = '1002'
ISSUED = '1000'
NEEDS_LOGIN = {'1101': 'login', '1102': 'verify'}
RELOGIN = '3203'
SESSION_CODES = {*NEEDS_LOGIN, RELOGIN}
TAX_RATES = {'0', '0.01', '0.03', '0.04', '0.05', '0.06', '0.09', '0.11', '0.13', '0.17'}
SHANGHAI_TZ = ZoneInfo('Asia/Shanghai')
UTC_TZ = ZoneInfo('UTC')
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
MAX_BASE64_FILE_BYTES = 10 * 1024 * 1024


class L10nCnEdiProviderUnreachable(UserError):
    """The request may have reached Yunshui, whose answer was lost: the outcome is unknown."""


class YunshuiClient:

    # Seconds to wait before each follow-up query of freshly submitted fapiao.
    result_delays = (3, 5)

    def __init__(self, company):
        self.company = company
        company_sudo = company.sudo()
        self.tax_no = company_sudo.vat or ''
        self.identity_code = company_sudo.l10n_cn_edi_yunshui_identity_code or ''
        self.platform_code = company_sudo.l10n_cn_edi_yunshui_platform_code or ''
        self.gateway = company_sudo.l10n_cn_edi_yunshui_gateway or 'test'
        self.username = company_sudo.l10n_cn_edi_yunshui_username or ''
        self.password = company_sudo.l10n_cn_edi_yunshui_password or ''

    def wait(self, seconds):
        time.sleep(seconds)

    def ensure_ready(self):
        if not self.company._l10n_cn_edi_is_ready():
            raise UserError(self.company.env._(
                "Yunshui is not set up for %(company)s: Tax ID, Identity Code and Platform Code are required.",
                company=self.company.name,
            ))

    def get_session_state(self):
        try:
            result = self._call(GET_CREDIT_LINE, {'nsrsbh': self.tax_no, 'cxbz': '1'})
        except YunshuiProviderError as e:
            if e.code in NEEDS_LOGIN:
                return NEEDS_LOGIN[e.code]
            raise
        if all(key in result for key in ('sysxed', 'ysysxed', 'zsxed')):
            return 'ok'
        raise UserError(self.company.env._(
            "Yunshui could not confirm tax-bureau session status. Please complete 'Tax Bureau Login' and retry.",
        ))

    def test_connection(self):
        self.ensure_ready()
        payload = {
            'fpqqlsh': f'ODOO-CONNECTION-TEST-{uuid.uuid4().hex[:16]}',
            'nsrsbh': self.tax_no,
            'invoiceKind': '82',
        }
        self._call(QUERY_RESULT, payload)

    def issue_invoice(self, values):
        code, message = self._submit(self._prepare_simple_issue_payload(values), values['invoice_type_code'])
        if code is None:
            return message
        if code == ISSUED:
            return {'state': 'sent'}
        return {
            'state': 'failed',
            'error': self.company.env._(
                "Yunshui refused the fapiao (%(code)s): %(message)s",
                code=code,
                message=message,
            ),
        }

    def issue_direct_red(self, values):
        payload = {
            'fpqqlsh': values['serial_no'],
            'nsrsbh': self.tax_no,
            'invoiceType': '2',
            'originInvoiceNo': values['original_fapiao_no'],
            'redReason': RED_REASONS[values['reason']],
            'invoiceKind': INVOICE_KIND[values['original_invoice_type_code']],
            'deliverType': '0',
        }
        code, message = self._submit(payload, values['original_invoice_type_code'])
        if code is None:
            return message
        if code == ISSUED:
            return {'state': 'sent'}
        return {
            'state': 'failed',
            'error': self.company.env._(
                "Yunshui refused the red invoice (%(code)s): %(message)s",
                code=code,
                message=message,
            ),
        }

    def query_invoice(self, document, just_submitted=False):
        code, response = self._query_code(document.serial_no, document.move_id.l10n_cn_edi_invoice_type_code)
        if result := self._query_outcome(document, code, response, just_submitted):
            return result
        return {
            'state': 'failed',
            'error': self.company.env._(
                "Yunshui failed to issue the fapiao (%(code)s): %(message)s",
                code=code,
                message=response.get('message') or '',
            ),
            'new_serial': True,
        }

    def query_red_form(self, document):
        raise UserError(self.company.env._(
            "Yunshui uses direct red invoice issuance; red confirmation-form polling is not supported.",
        ))

    def operate_red_form(self, document, action):
        raise UserError(self.company.env._(
            "Yunshui does not support %(action)s on red forms from Odoo yet.",
            action=action,
        ))

    def list_inbound_red_forms(self, date_from, date_to):
        # 2.1.11 only queries the red-confirmation form of a known fpqqlsh, it has no date-range listing.
        raise UserError(self.company.env._(
            "Yunshui does not support listing inbound red forms by date range.",
        ))

    def login_step(self, step_name, **extra_payload):
        self.ensure_ready()
        if not self.username:
            raise UserError(self.company.env._(
                "Yunshui login needs an E-Tax Username in the company settings.",
            ))
        payload = {
            'step_name': step_name,
            'nsrsbh': self.tax_no,
            'username': self.username,
            **extra_payload,
        }
        if self.company.l10n_cn_edi_yunshui_region_code and 'dqbm' not in payload:
            payload['dqbm'] = self.company.l10n_cn_edi_yunshui_region_code
        if step_name == 'login':
            if self.password:
                payload['password'] = self.password
            if self.company.sudo().l10n_cn_edi_yunshui_relogin:
                payload['reloginflag'] = 'true'
        result = self._call(LOGIN, payload)
        if str(result.get('step_code') or '') == '6':
            raise UserError(result.get('message') or self.company.env._("Yunshui login failed."))
        return result

    def _submit(self, payload, invoice_type_code):
        """Send ``payload`` to simpleInvoiceIssue: ``(code, message)``, or ``(None, result)`` once reconciled."""
        try:
            response = self._call(SIMPLE_ISSUE, payload)
        except YunshuiProviderError as e:
            if e.code == '9994':
                return None, self._reconcile_existing_order(payload['fpqqlsh'], invoice_type_code)
            code, message = e.code, e.msg
        else:
            code, message = str(response.get('code') or ''), response.get('message') or ''
        self._check_session(code, message)
        return code, message

    def _check_session(self, code, message):
        if code == RELOGIN:
            self.company.sudo().l10n_cn_edi_yunshui_relogin = True
        if code in SESSION_CODES:
            raise UserError(self._login_error(code, message))

    def _query_result(self, serial_no, invoice_type_code):
        return self._call(QUERY_RESULT, {
            'fpqqlsh': serial_no,
            'nsrsbh': self.tax_no,
            'invoiceKind': INVOICE_KIND[invoice_type_code],
        })

    def _query_code(self, serial_no, invoice_type_code):
        """queryResult's code and response, the session codes being read off the outer envelope too."""
        try:
            response = self._query_result(serial_no, invoice_type_code)
        except YunshuiProviderError as e:
            if e.code not in SESSION_CODES:
                raise
            response = {'code': e.code, 'message': e.msg}
        return str(response.get('code') or ''), response

    def _query_outcome(self, document, code, response, just_submitted):
        """Return the result of a queryResult code that isn't a definitive failure, else None."""
        if code == ISSUED:
            invoice_kind = INVOICE_KIND[document.move_id.l10n_cn_edi_invoice_type_code]
            result = self._issued_result(response, serial_no=document.serial_no, invoice_kind=invoice_kind)
            if document.move_id.move_type == 'out_refund':
                result.update(self._red_form_of(document.serial_no, invoice_kind))
            return result
        if code == RELOGIN:
            # Recorded rather than raised: the poll cron's savepoint would roll the flag back with the error.
            self.company.sudo().l10n_cn_edi_yunshui_relogin = True
            _logger.warning("Yunshui asks company %s to log in again (3203)", self.company.vat)
            return {'state': 'sent'}
        self._check_session(code, response.get('message') or '')
        if code == PENDING or just_submitted:
            return {'state': 'sent'}
        return None

    def _red_form_of(self, serial_no, invoice_kind):
        """The red form the bureau recorded for the red fapiao issued under ``serial_no`` (2.1.11)."""
        try:
            response = self._call(QUERY_RED_FORM, {'fpqqlsh': serial_no, 'invoiceKind': invoice_kind})
        except UserError as e:
            _logger.warning("Yunshui: could not read the red form of %s for company %s: %s", serial_no, self.company.vat, e)
            return {}
        return {'red_form_uuid': response.get('uuid'), 'red_form_number': response.get('hzfpxxqrdbh')}

    def _prepare_simple_issue_payload(self, values):
        for line in values['lines']:
            if line.get('vat_special_policy') or line.get('reduced_tax_code'):
                raise UserError(self.company.env._(
                    "Yunshui simple issuance does not support special VAT treatment for line %(line)s (%(name)s).",
                    line=line['line_no'],
                    name=line['name'],
                ))
        payload = {
            'fpqqlsh': values['serial_no'],
            'nsrsbh': self.tax_no,
            'invoiceKind': INVOICE_KIND[values['invoice_type_code']],
            'invoiceType': '1',
            'businessType': '0' if values['buyer_is_natural_person'] else '1',
            'invoiceAmount': f"{values['amount_total']:.2f}",
            'payerName': values['buyer_name'],
            'deliverType': '0',
            'bz': values['remark'],
            'invoiceItems': [self._prepare_simple_line(line) for line in values['lines']],
        }
        if self.company.l10n_cn_edi_drawer:
            payload['invoicer'] = self.company.l10n_cn_edi_drawer
        if values['buyer_tax_no']:
            payload['payerRegisterNo'] = values['buyer_tax_no']
        if values['buyer_address']:
            payload['payerAddress'] = values['buyer_address']
        if values['buyer_phone']:
            payload['payerPhone'] = values['buyer_phone']
        if values['buyer_address'] or values['buyer_phone']:
            payload['sfzsgmfdzdh'] = 'Y'
        if values['buyer_bank_name']:
            payload['payerBank'] = values['buyer_bank_name']
        if values['buyer_bank_account']:
            payload['payerBankaccount'] = values['buyer_bank_account']
        if values['buyer_bank_name'] or values['buyer_bank_account']:
            payload['sfzsgmfyhzh'] = 'Y'
        return payload

    def _prepare_simple_line(self, line):
        self._validate_line_values(line)
        detail = {
            'rowType': line['nature'],
            'itemName': line['name'],
            'amount': f"{line['amount_total']:.2f}",
            'taxRate': _format_rate(line['tax_rate']),
            'itemNo': line['tax_category_code'],
        }
        if line['quantity']:
            detail['quantity'] = _format_quantity(line['quantity'])
        if line['uom']:
            detail['unit'] = line['uom']
        if line.get('free_tax_mark'):
            detail['zeroRateFlag'] = line['free_tax_mark']
        return detail

    def _validate_line_values(self, line):
        if _decimal_places(line['quantity']) > 13:
            raise UserError(self.company.env._(
                "Yunshui quantity supports at most 13 decimal places (line %(line)s: %(name)s).",
                line=line['line_no'],
                name=line['name'],
            ))
        if _format_rate(line['tax_rate']) not in TAX_RATES:
            raise UserError(self.company.env._(
                "Yunshui does not accept a %(rate)s%% tax rate (line %(line)s: %(name)s).",
                rate=round(line['tax_rate'] * 100, 2),
                line=line['line_no'],
                name=line['name'],
            ))

    def _issued_result(self, response, serial_no=None, invoice_kind=None):
        fapiao_no = response.get('fphm')
        date_value = response.get('kprq')
        fapiao_date = False
        if date_value:
            shanghai_time = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=SHANGHAI_TZ)
            fapiao_date = shanghai_time.astimezone(UTC_TZ).replace(tzinfo=None)
        result = {
            'state': 'issued',
            'fapiao_no': fapiao_no,
            'fapiao_date': fapiao_date,
            'qr_code': response.get('ewmUrl') or False,
        }
        for kind, field in (('pdf', 'pdfUrl'), ('ofd', 'ofdUrl')):
            content = self._download(response.get(field))
            if content and self._is_expected_file(kind, content):
                result.update({kind: content, f'{kind}_filename': f'{fapiao_no}.{kind}'})
                continue
            if content:
                _logger.warning(
                    "Yunshui: ignored malformed %s payload from query_result for company %s",
                    kind,
                    self.company.vat,
                )
            if serial_no and invoice_kind:
                content = self._download_invoice_file(serial_no, invoice_kind, kind)
                if content:
                    result.update({kind: content, f'{kind}_filename': f'{fapiao_no}.{kind}'})
        return result

    def _download_invoice_file(self, serial_no, invoice_kind, kind):
        file_type = '1' if kind == 'pdf' else '2'
        try:
            response = self._call(DOWNLOAD_INVOICE, {
                'fpqqlsh': serial_no,
                'invoiceKind': invoice_kind,
                'fileType': file_type,
            })
        except UserError as e:
            _logger.warning("Yunshui: could not download %s through API for company %s: %s", kind, self.company.vat, e)
            return None
        content = self._decode_base64_file(response.get('file'))
        if content and self._is_expected_file(kind, content):
            return content
        if content:
            _logger.warning("Yunshui: ignored malformed %s blob from invoice.download for company %s", kind, self.company.vat)
        if kind != 'pdf':
            return None
        content = self._download(response.get('pdfUrl'))
        if content and self._is_expected_file(kind, content):
            return content
        if content:
            _logger.warning("Yunshui: ignored malformed %s blob from invoice.download URL for company %s", kind, self.company.vat)
        return None

    def _decode_base64_file(self, value):
        if not value:
            return None
        if len(value) > ((MAX_BASE64_FILE_BYTES * 4) // 3) + 8:
            _logger.warning("Yunshui: base64 file payload too large for company %s", self.company.vat)
            return None
        try:
            content = b64decode(value, validate=True)
        except (BinasciiError, ValueError, TypeError) as e:
            _logger.warning("Yunshui: invalid base64 file payload for company %s: %s", self.company.vat, e)
            return None
        if len(content) > MAX_BASE64_FILE_BYTES:
            _logger.warning("Yunshui: decoded file payload too large for company %s (%s bytes)", self.company.vat, len(content))
            return None
        return content

    def _is_expected_file(self, kind, content):
        if not content:
            return False
        if kind == 'pdf':
            return content.startswith(b'%PDF')
        if kind == 'ofd':
            return content.startswith(b'PK')
        return False

    def _download(self, url):
        if not url:
            return None
        host = _url_host(url)
        if not self._is_safe_download_url(url):
            _logger.warning("Yunshui: blocked non-https file URL on %s for company %s", host, self.company.vat)
            return None
        try:
            with requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True) as response:
                response.raise_for_status()
                content = _read_capped(response, MAX_DOWNLOAD_BYTES)
        except requests.RequestException as e:
            _logger.warning("Yunshui: could not download file from %s for company %s: %s", host, self.company.vat, type(e).__name__)
            return None
        if content is None:
            _logger.warning("Yunshui: file download from %s too large for company %s", host, self.company.vat)
        return content

    def _is_safe_download_url(self, url):
        try:
            parsed = urlparse(url)
            return parsed.scheme == 'https' and bool(parsed.hostname)
        except ValueError:
            return False

    def _call(self, interface_code, payload):
        request_body = sm4_envelope.build_request(
            interface_code,
            payload,
            self.identity_code,
            self.platform_code,
            self.tax_no,
        )
        try:
            with requests.post(
                f"{HOSTS[self.gateway]}/{interface_code}",
                data=json.dumps(request_body, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                timeout=TIMEOUT,
                stream=True,
            ) as response:
                response.raise_for_status()
                body = _read_capped(response, MAX_RESPONSE_BYTES)
        except requests.ConnectTimeout as e:
            _logger.warning("Yunshui %s failed for company %s: %s", interface_code, self.company.vat, e)
            raise UserError(self.company.env._("Could not reach Yunshui. Please try again later.")) from e
        except requests.RequestException as e:
            # The request may have gone through: only a query can tell.
            _logger.warning("Yunshui %s failed for company %s: %s", interface_code, self.company.vat, e)
            raise L10nCnEdiProviderUnreachable(self.company.env._("Yunshui did not answer. Please try again later.")) from e
        try:
            return sm4_envelope.verify_and_decrypt(
                _load_response(body),
                self.identity_code,
                self.platform_code,
            )
        except (ValueError, sm4_envelope.MalformedEnvelope) as e:
            _logger.warning("Yunshui %s sent an unreadable response for company %s: %s", interface_code, self.company.vat, e)
            raise L10nCnEdiProviderUnreachable(self.company.env._(
                "Yunshui sent a response Odoo could not read. Please try again later.",
            )) from e
        except sm4_envelope.YunshuiProtocolError as e:
            raise YunshuiProviderError(e.code, e.msg, self.company.env._(
                "Yunshui protocol error %(code)s: %(message)s",
                code=e.code,
                message=e.msg,
            )) from e

    def _reconcile_existing_order(self, serial_no, invoice_type_code):
        try:
            result = self._query_result(serial_no, invoice_type_code)
        except YunshuiProviderError as e:
            return {
                'state': 'failed',
                'error': self.company.env._(
                    "Yunshui could not reconcile duplicate order %(serial)s (%(code)s).",
                    serial=serial_no,
                    code=e.code,
                ),
            }
        code = str(result.get('code') or '')
        if code in {ISSUED, PENDING}:
            return {'state': 'sent'}
        self._check_session(code, result.get('message') or '')
        return {
            'state': 'failed',
            'error': self.company.env._(
                "Yunshui could not reconcile duplicate order %(serial)s (%(code)s).",
                serial=serial_no,
                code=code,
            ),
            'new_serial': True,
        }

    def _verify_error(self):
        return self.company.env._(
            "The tax bureau asks the drawer of %(company)s for real-person authentication (实人认证), "
            "which Odoo can't do yet: complete it in the Aisino Yunshui portal, then send the invoices again.",
            company=self.company.name,
        )

    def _login_error(self, code, message):
        if code == '1102':
            return self._verify_error()
        return self.company.env._(
            "Yunshui requires tax-bureau login: %(message)s",
            message=message,
        )


def _format_rate(number):
    return f"{number:.8f}".rstrip('0').rstrip('.')


def _format_quantity(number):
    return f"{number:.13f}".rstrip('0').rstrip('.')


def _decimal_places(number):
    try:
        decimal = Decimal(str(number)).normalize()
    except (InvalidOperation, ValueError, TypeError):
        return 0
    return max(-int(decimal.as_tuple().exponent), 0)


def _load_response(body):
    """Decode a response body, ``None`` when it was over the cap."""
    if body is None:
        error = 'response too large'
        raise sm4_envelope.MalformedEnvelope(error)
    return json.loads(body)


def _read_capped(response, limit):
    """The body of a streamed ``response``, or None past ``limit`` bytes."""
    content = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        content += chunk
        if len(content) > limit:
            return None
    return bytes(content)


def _url_host(url):
    try:
        return urlparse(url).hostname or ''
    except ValueError:
        return ''


class YunshuiProviderError(UserError):
    def __init__(self, code, msg, message):
        self.code = str(code or '')
        self.msg = msg or ''
        super().__init__(message)
