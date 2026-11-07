# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import json
import logging
import time
import uuid
import zipfile
from base64 import b64decode
from binascii import Error as BinasciiError
from datetime import datetime, timedelta
from urllib.parse import urlsplit
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
H5_PASS_THROUGH = 'ele.h5.pass.through'
BLUE_LIST = 'h5.js.blueInkInvoiceList.query'
RED_FORM_INIT = 'h5.js.RedConfirmationDetail.init'
RED_FORM_ISSUE = 'h5.js.redConfirmationSheet.issue'
RED_FORM_DETAIL = 'h5.js.redInvoiceConfirmDetail.query'
RED_FORM_UPDATE = 'h5.js.redInkConfirmationStatus.update'
RED_FORM_LIST = 'h5.js.redInvoiceConfirmList.query'
H5_DOWNLOAD = 'h5.js.invoice.download'
RED_FORM_ACTIONS = {'confirm': '1', 'reject': '2', 'revoke': '3'}
ACTIVE_RED_FORM_STATES = {'01', '02', '03', '04'}
RED_FORM_PAGE_SIZE = 50

INVOICE_KIND = {'01': '81', '02': '82'}
PENDING = '1002'
ISSUED = '1000'
NEEDS_LOGIN = {'1101': 'login', '1102': 'verify'}
RELOGIN = '3203'
SESSION_CODES = {*NEEDS_LOGIN, RELOGIN}
SHANGHAI_TZ = ZoneInfo('Asia/Shanghai')
UTC_TZ = ZoneInfo('UTC')
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
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

    def issue(self, payload):
        """Submit a simpleInvoiceIssue ``payload`` (2.1.2)."""
        code, message = self._submit(payload)
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

    def query_invoice(self, document, just_submitted=False):
        invoice_kind = INVOICE_KIND[document.move_id.l10n_cn_edi_invoice_type_code]
        code, response = self._query_code(document.serial_no, invoice_kind)
        if result := self._query_outcome(document, invoice_kind, code, response, just_submitted):
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

    def request_red_form(self, document):
        """
        Raise the red form of ``document``'s credit note against its whole fapiao (3.2.7, 3.2.20, 3.2.5).

        The bureau fills the form in from the fapiao; 3.2.5 takes it back with its own field names
        added, and the total in words it requires. When the buyer needn't confirm, the bureau
        issues the red fapiao right away.
        """
        original = document.move_id.reversed_entry_id
        fapiao_no = original.l10n_cn_edi_fapiao_no
        issued_on = self._shanghai(original.l10n_cn_edi_fapiao_date).date() if original.l10n_cn_edi_fapiao_date else original.invoice_date
        found = self._h5(BLUE_LIST, {
            'gxfxz': '0',
            'fp_hm': fapiao_no,
            # A day around it: the date Odoo has may differ from the bureau's by a few seconds.
            'kprqq': str(issued_on - timedelta(days=1)),
            'kprqz': str(issued_on + timedelta(days=1)),
            'cxym': '1',
            'ts': '10',
        })
        blue = next((row for row in found.get('list') or [] if row.get('fp_hm') == fapiao_no), None)
        if not blue:
            # 3.2.5 takes no serial: when its answer got lost, the form exists and the fapiao isn't offered anymore.
            requested_on = self._shanghai(document.create_date).date()
            if form := next((
                form for form in self._red_forms('0', '0', requested_on - timedelta(days=1), requested_on + timedelta(days=1))
                if form['original_fapiao_no'] == fapiao_no and form['bureau_state'] in ACTIVE_RED_FORM_STATES
            ), None):
                return self._red_form_result(self._h5(RED_FORM_DETAIL, {'uuid': form['uuid'], 'xhf_nsrsbh': self.tax_no}))
            raise UserError(self.company.env._(
                "The tax bureau doesn't offer fapiao %(fapiao)s for a red form: it may already be reversed.",
                fapiao=fapiao_no,
            ))
        form = self._h5(RED_FORM_INIT, {
            'lzfpqdhm': fapiao_no,
            'xsfnsrsbh': self.tax_no,
            'lzkprq': blue.get('kprq'),
            'sflzfp': blue.get('sflzfp'),
            'fply_dm': blue.get('fply_dm'),
            'gjbq': blue.get('gjbq'),
            'fplxdm': blue.get('fplx_dm'),
            'gmfnsrsbh': blue.get('ghf_nsrsbh'),
            'kpfnsrsbh': blue.get('kpfnsrsbh'),
            'tdyslxdm': blue.get('tdyslx_dm'),
            'lrfsf': '0',
        })
        form.pop('code', None)
        form.pop('message', None)
        answer = self._h5(RED_FORM_ISSUE, {
            **form,
            'lzfpqd_hm': form.get('lzfphm'),
            'xhf_nsrsbh': form.get('xsfnsrsbh'),
            'xhf_mc': form.get('xsfmc'),
            'ghf_nsrsbh': form.get('gmfnsrsbh'),
            'ghf_mc': form.get('gmfmc'),
            'lzfppzdm': form.get('lzfppz_dm'),
            'lzfplxdm2': form.get('lzfplx_dm2'),
            'zzsytdm': form.get('zzsyt_dm'),
            'xfsytdm': form.get('xfsyt_dm'),
            'fprzztdm': form.get('fprzzt_dm'),
            'hzqrxxztdm': form.get('hzqrxxzt_dm'),
            'fplydm': form.get('fply_dm'),
            'hzqrxxmxlist': [{**line, 'sl': line.get('sl1')} for line in form.get('hzqrxxmx_list') or []],
            'jshjdx': _amount_in_words(form.get('jshj') or 0),
            'chyydm': document.red_form_reason,
            'chyy_dm': document.red_form_reason,
            'nsrsbh': self.tax_no,
        })
        return self._red_form_result(answer)

    def query_red_form(self, document):
        return self._red_form_result(self._h5(RED_FORM_DETAIL, {
            'uuid': document.red_form_uuid,
            'xhf_nsrsbh': self._seller_tax_no(document),
        }))

    def operate_red_form(self, document, action):
        self._h5(RED_FORM_UPDATE, {
            'uuid': document.red_form_uuid,
            'xhf_nsrsbh': self._seller_tax_no(document),
            'czlx': RED_FORM_ACTIONS[action],
        })

    def list_inbound_red_forms(self, date_from, date_to):
        """The red forms raised against us, as the seller of our invoices and the buyer of our bills (3.2.6)."""
        # A form can come twice: on both sides when we bought from ourselves, or on two pages when a new one shifts the list.
        return list({form['uuid']: form for side in ('0', '1') for form in self._red_forms(side, '1', date_from, date_to)}.values())

    def _red_forms(self, side, direction, date_from, date_to):
        """The red forms of ``side`` (0 seller, 1 buyer) we raised (``direction`` 0) or received (1), page by page."""
        forms, page = [], 1
        while True:
            answer = self._h5(RED_FORM_LIST, {
                'gxfxz': side,
                'cxlx': direction,
                'kprqq': str(date_from),
                'kprqz': str(date_to),
                'cxym': str(page),
                'ts': str(RED_FORM_PAGE_SIZE),
            })
            rows = answer.get('list') or []
            forms += [{
                **self._red_form_result(row, with_files=False),
                'original_fapiao_no': row.get('lzfphm'),
                'amount_untaxed': float(row.get('hzcxje') or 0),
                'amount_tax': float(row.get('hzcxse') or 0),
                'reason': row.get('chyydm'),
            } for row in rows]
            if len(rows) < RED_FORM_PAGE_SIZE or page * RED_FORM_PAGE_SIZE >= int(answer.get('total') or 0):
                return forms
            page += 1

    def _seller_tax_no(self, document):
        """The seller of a red form's fapiao: us on our invoices, the supplier on our bills."""
        move = document.move_id
        return move.commercial_partner_id.vat if move.is_purchase_document() else self.tax_no

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

    def _submit(self, payload):
        """Send ``payload`` to simpleInvoiceIssue: ``(code, message)``, or ``(None, result)`` once reconciled."""
        try:
            response = self._call(SIMPLE_ISSUE, payload)
        except YunshuiProviderError as e:
            if e.code == '9994':
                return None, self._reconcile_existing_order(payload['fpqqlsh'], payload['invoiceKind'])
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

    def _query_result(self, serial_no, invoice_kind):
        return self._call(QUERY_RESULT, {
            'fpqqlsh': serial_no,
            'nsrsbh': self.tax_no,
            'invoiceKind': invoice_kind,
        })

    def _query_code(self, serial_no, invoice_kind):
        """queryResult's code and response, the session codes being read off the outer envelope too."""
        try:
            response = self._query_result(serial_no, invoice_kind)
        except YunshuiProviderError as e:
            if e.code not in SESSION_CODES:
                raise
            response = {'code': e.code, 'message': e.msg}
        return str(response.get('code') or ''), response

    def _query_outcome(self, document, invoice_kind, code, response, just_submitted):
        """Return the result of a queryResult code that isn't a definitive failure, else None."""
        if code == ISSUED:
            return self._issued_result(response, serial_no=document.serial_no, invoice_kind=invoice_kind)
        if code == RELOGIN:
            # Recorded rather than raised: the poll cron's savepoint would roll the flag back with the error.
            self.company.sudo().l10n_cn_edi_yunshui_relogin = True
            _logger.warning("Yunshui asks company %s to log in again (3203)", self.company.vat)
            return {'state': 'sent'}
        self._check_session(code, response.get('message') or '')
        if code == PENDING or just_submitted:
            return {'state': 'sent'}
        return None

    def _red_form_result(self, answer, with_files=True):
        """The red form of a 3.2.5, 3.2.1 or 3.2.6 ``answer``, with its red fapiao and that fapiao's files once issued."""
        result = {
            'uuid': answer.get('uuid'),
            'number': answer.get('hzfpxxqrdbh'),
            'bureau_state': answer.get('hzqrxxzt_dm') or answer.get('hzqrxxztdm'),
            'red_fapiao_no': answer.get('hzfp_hm'),
        }
        if result['red_fapiao_no'] and answer.get('hzkprq'):
            result['red_fapiao_date'] = self._utc(answer['hzkprq'])
            if with_files:
                result.update(self._fapiao_files(result['red_fapiao_no'], answer['hzkprq']))
        return result

    def _fapiao_files(self, fapiao_no, issued_at):
        """The links to a fapiao's PDF and OFD, and its XML, by its number (3.2.9)."""
        payload = {
            'fp_hm': fapiao_no,
            'kprq': issued_at.replace('-', '').replace(':', '').replace(' ', ''),
            'xsfnsrsbh': self.tax_no,
            'nsrsbh': self.tax_no,
            'dqbm': self.company.l10n_cn_edi_yunshui_region_code,
        }
        files = {}
        try:
            for key, file_type in (('pdf_url', '0'), ('ofd_url', '1')):
                files[key] = self._https_url(self._h5(H5_DOWNLOAD, {**payload, 'xzlx': file_type, 'isurl_flag': 'true'}).get('jfdljUrl'))
            files['xml'] = self._unzip_xml(self._h5(H5_DOWNLOAD, {**payload, 'xzlx': '2'}).get('wjl'), fapiao_no)
        except UserError as e:
            _logger.warning("Yunshui: could not fetch the files of fapiao %s for company %s: %s", fapiao_no, self.company.vat, e)
        return files

    def _issued_result(self, response, serial_no=None, invoice_kind=None):
        result = {
            'state': 'issued',
            'fapiao_no': response.get('fphm'),
            'fapiao_date': self._utc(response['kprq']) if response.get('kprq') else False,
            'qr_code': response.get('ewmUrl') or False,
            # Yunshui's links to the PDF and OFD can come after the fapiao itself: the cron fills them in later.
            'pdf_url': self._https_url(response.get('pdfUrl')),
            'ofd_url': self._https_url(response.get('ofdUrl')),
        }
        if serial_no and invoice_kind:
            result['xml'] = self._download_xml(serial_no, invoice_kind)
        return result

    def _download_xml(self, serial_no, invoice_kind):
        """The fapiao's XML, the record the law has the company keep (2.1.10). Yunshui zips it."""
        try:
            response = self._call(DOWNLOAD_INVOICE, {'fpqqlsh': serial_no, 'invoiceKind': invoice_kind, 'fileType': '3'})
        except UserError as e:
            _logger.warning("Yunshui: could not download the XML of %s for company %s: %s", serial_no, self.company.vat, e)
            return None
        return self._unzip_xml(response.get('file'), serial_no)

    def _unzip_xml(self, value, reference):
        """The XML in the base64 zip ``value`` Yunshui sends it in."""
        content = self._decode_base64_file(value)
        if not content:
            return None
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                member = next((info for info in archive.infolist() if info.filename.endswith('.xml')), None)
                xml = archive.read(member) if member and member.file_size <= MAX_BASE64_FILE_BYTES else None
        except zipfile.BadZipFile:
            xml = None
        if not xml:
            _logger.warning("Yunshui: ignored a malformed XML archive of %s for company %s", reference, self.company.vat)
        return xml

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

    def _utc(self, shanghai_time):
        """A naive UTC datetime from Yunshui's Shanghai ``'%Y-%m-%d %H:%M:%S'``."""
        return datetime.strptime(shanghai_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=SHANGHAI_TZ).astimezone(UTC_TZ).replace(tzinfo=None)

    def _shanghai(self, utc_time):
        return utc_time.replace(tzinfo=UTC_TZ).astimezone(SHANGHAI_TZ)

    def _h5(self, interface_code, payload):
        """Call a chapter 3 interface: they go through the H5 pass-through, as the logged-in drawer."""
        try:
            answer = self._call(interface_code, {key: value for key, value in payload.items() if value not in (None, '')}, h5=True)
        except YunshuiProviderError as e:
            self._check_session(e.code, e.msg)
            raise
        if answer.get('code') == 'N':
            raise UserError(answer.get('message') or self.company.env._("The tax bureau refused the request."))
        return answer

    def _https_url(self, url):
        try:
            parsed = urlsplit(url or '')
        except ValueError:
            return False
        return url if parsed.scheme == 'https' and parsed.hostname else False

    def _call(self, interface_code, payload, h5=False):
        request_body = sm4_envelope.build_request(
            interface_code,
            payload,
            self.identity_code,
            self.platform_code,
            self.tax_no,
        )
        try:
            with requests.post(
                f"{HOSTS[self.gateway]}/{H5_PASS_THROUGH if h5 else interface_code}",
                data=json.dumps(request_body, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json', **({'X-KPY-YHM': self.username} if h5 else {})},
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

    def _reconcile_existing_order(self, serial_no, invoice_kind):
        try:
            result = self._query_result(serial_no, invoice_kind)
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


def _amount_in_words(amount):
    """``amount`` the way a fapiao writes its total: 1060.5 -> 壹仟零陆拾圆伍角整."""
    digits, units, groups = '零壹贰叁肆伍陆柒捌玖', ('', '拾', '佰', '仟'), ('', '万', '亿', '万亿')
    cents = round(abs(float(amount)) * 100)
    yuan, jiao, fen = cents // 100, cents // 10 % 10, cents % 10
    words, gap = '', False
    group_values = []
    while yuan:
        group_values.append(yuan % 10000)
        yuan //= 10000
    for index in range(len(group_values) - 1, -1, -1):
        value = group_values[index]
        if not value:
            gap = bool(words)
            continue
        if words and (gap or value < 1000):
            words += '零'
        part, zero = '', False
        for position in range(3, -1, -1):
            digit = value // 10 ** position % 10
            if digit:
                part += ('零' if zero and part else '') + digits[digit] + units[position]
            zero = not digit
        words += part + groups[index]
        gap = False
    words += '圆' if words else ''
    if not (jiao or fen):
        return (words or '零圆') + '整'
    words += digits[jiao] + '角' if jiao else ('零' if words else '')
    return words + (digits[fen] + '分' if fen else '整')


class YunshuiProviderError(UserError):
    def __init__(self, code, msg, message):
        self.code = str(code or '')
        self.msg = msg or ''
        super().__init__(message)
