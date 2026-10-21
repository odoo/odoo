# -*- coding: utf-8 -*-
from datetime import timedelta

import requests
from requests import RequestException

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

EHOADON_TIMEOUT = 60


class EhoadonConfig(models.Model):
    _name = 'ehoadon.config'
    _description = 'eHoaDon Online Configuration'

    name = fields.Char(string='Name', default='eHoaDon configuration', required=True)
    tax_number = fields.Char(
        string='Tax number (host)',
        help='MST công ty trên eHoaDon → host https://{MST}.ehoadon.net. '
             'Không dùng 0123456789 (host demo swagger).',
        required=False,
    )
    endpoint_host = fields.Char(
        string='API host override',
        help='Optional full origin, e.g. https://0312345678.ehoadon.net. '
             'If empty, built from tax_number.',
    )
    email = fields.Char(
        string='API Email',
        help='Email tài khoản API (Hệ thống → Quản trị người dùng → Thông tin API). '
             'Không điền MST vào đây.',
    )
    password = fields.Char(string='API Password')
    tenant_id = fields.Char(
        string='Tenant ID',
        help='TenantId bắt buộc theo docs eHoaDon (thường lấy từ Thông tin API). '
             'Nếu trống, hệ thống thử dùng Tax number (host).',
    )
    access_token = fields.Char(string='Access Token (cache)', readonly=True)
    access_token_expiry = fields.Datetime(string='Access Token Expiry', readonly=True)
    refresh_token = fields.Char(string='Refresh Token (cache)', readonly=True)
    default_template_id = fields.Many2one(
        'ehoadon.template',
        string='Default Invoice Template',
    )
    template_ids = fields.One2many(
        'ehoadon.template',
        'config_id',
        string='Invoice Templates',
    )

    _sql_constraints = [
        ('unique_config', 'CHECK(1=1)', 'Only one configuration is allowed.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if len(vals_list) > 1 or self.search([], limit=1):
            raise ValidationError(
                _('Chỉ được phép có một cấu hình eHoaDon. Vui lòng chỉnh sửa cấu hình hiện tại.')
            )
        return super().create(vals_list)

    @api.model
    def get_ehoadon_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({
                'name': 'Cấu hình eHoaDon',
                'tax_number': '',
            })
        return config

    @api.model
    def get_or_create_config(self):
        config = self.search([], limit=1)
        if not config:
            if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_manager'):
                raise UserError(_(
                    'Chưa có cấu hình eHoaDon. Vui lòng liên hệ quản trị (eHoaDon Manager).'
                ))
            config = self.create({
                'name': 'Cấu hình eHoaDon',
                'tax_number': '',
            })
        return config

    def _ehoadon_base_url(self, template=None):
        self.ensure_one()
        override = (
            (template and getattr(template, 'endpoint_host', False))
            or self.endpoint_host
            or ''
        ).strip()
        if override:
            base = override.rstrip('/')
        else:
            tax = (
                (template and getattr(template, 'tax_number', False))
                or self.tax_number
                or ''
            ).strip()
            if not tax:
                raise UserError(_('Thiếu mã số thuế (tax_number) để dựng host eHoaDon.'))
            base = 'https://%s.ehoadon.net' % tax
        return base

    def api_url(self, path, template=None):
        self.ensure_one()
        path = (path or '').lstrip('/')
        return '%s/%s' % (self._ehoadon_base_url(template=template), path)

    def _ehoadon_flatten_field_errors(self, errors):
        """Flatten Errors / errors dict from eHoaDon (PascalCase or camelCase)."""
        if not isinstance(errors, dict):
            return []
        parts = []
        for key, val in errors.items():
            if isinstance(val, (list, tuple)):
                msg = '; '.join(str(x) for x in val)
            else:
                msg = str(val)
            if not msg or msg == 'None':
                continue
            if key:
                parts.append('%s: %s' % (key, msg))
            else:
                parts.append(msg)
        return parts

    def _ehoadon_extract_data_field_errors(self, resp_json):
        """Return field-error strings from resp.data.Errors / data.errors."""
        if not isinstance(resp_json, dict):
            return []
        data = resp_json.get('data')
        if not isinstance(data, dict):
            return []
        return self._ehoadon_flatten_field_errors(
            data.get('Errors') or data.get('errors')
        )

    def _ehoadon_extract_publish_failure(self, resp_json):
        """PublishInvoice may return HTTP 200 + data.Status=False + Message."""
        if not isinstance(resp_json, dict):
            return None
        data = resp_json.get('data')
        # Some responses put Message/Status at top level
        candidates = []
        if isinstance(data, dict):
            candidates.append(data)
        candidates.append(resp_json)
        for block in candidates:
            status_flag = block.get('Status')
            if status_flag is None:
                status_flag = block.get('status')
            msg = block.get('Message') or block.get('message')
            err_ids = block.get('ErrorInvoiceIds') or block.get('errorInvoiceIds')
            # Explicit business failure
            if status_flag is False or (err_ids and msg):
                return msg or _('PublishInvoice thất bại (Status=False).')
            if msg and isinstance(status_flag, str) and status_flag.lower() in ('false', 'error', 'fail'):
                return msg
        return None

    def _ehoadon_format_error_detail(self, resp_json, response):
        """Extract human-readable detail from eHoaDon / ASP.NET ProblemDetails."""
        if not isinstance(resp_json, dict):
            return response.reason or 'Unknown error'
        parts = []
        pub_msg = self._ehoadon_extract_publish_failure(resp_json)
        if pub_msg:
            parts.append(pub_msg)
        # Prefer nested AddEInvoice field errors (Serial, …) over dumping whole data.
        parts.extend(self._ehoadon_extract_data_field_errors(resp_json))
        parts.extend(self._ehoadon_flatten_field_errors(
            resp_json.get('errors') or resp_json.get('Errors')
        ))
        for key in ('title', 'message', 'detail', 'Message'):
            val = resp_json.get(key)
            if val and str(val) not in parts:
                parts.append(str(val))
        if not parts:
            data = resp_json.get('data')
            if isinstance(data, dict):
                msg = data.get('Message') or data.get('message')
                if msg:
                    parts.append(str(msg))
                elif data not in (None, {}, []):
                    parts.append(str(data))
            elif data and data not in (None, {}, []):
                parts.append(str(data))
        raw = resp_json.get('_raw_text')
        if raw:
            parts.append(str(raw)[:500])
        if parts:
            return ' | '.join(parts)
        return response.reason or 'Unknown error'

    def _ehoadon_send_request(
        self,
        method,
        url,
        json_data=None,
        headers=None,
        timeout=EHOADON_TIMEOUT,
    ):
        """Return (resp_json, error_message)."""
        try:
            response = requests.request(
                method,
                url,
                json=json_data,
                headers=headers or {},
                timeout=timeout,
            )
            try:
                resp_json = response.json()
            except ValueError:
                resp_json = {}
                text = (response.text or '').strip()
                if text:
                    resp_json['_raw_text'] = text[:2000]
                    # Token/Create docs return bare JWT as text/plain (HTTP 200).
                    if response.status_code < 400 and text.count('.') >= 2:
                        resp_json['accessToken'] = text
                        resp_json['status'] = 'success'

            if not isinstance(resp_json, dict):
                # Rare: JSON decoded to a bare string (token)
                if isinstance(resp_json, str) and response.status_code < 400:
                    resp_json = {
                        'accessToken': resp_json,
                        'status': 'success',
                        '_raw_text': resp_json[:2000],
                    }
                else:
                    resp_json = {'_raw': resp_json}

            resp_json['_odoo_http'] = {
                'url': url,
                'method': method,
                'status_code': response.status_code,
            }

            error = None
            # Swagger: status may be string ("success"/"error") OR int HttpStatusCode (200/400…).
            raw_status = resp_json.get('status')
            if isinstance(raw_status, str):
                api_bad = raw_status.strip().lower() == 'error'
            elif isinstance(raw_status, int):
                api_bad = raw_status >= 400
            else:
                api_bad = False
            # AddEInvoice may return HTTP 200 + data.Errors even when status is odd.
            field_errors = self._ehoadon_extract_data_field_errors(resp_json)
            publish_fail = self._ehoadon_extract_publish_failure(resp_json)
            http_bad = response.status_code >= 400
            if http_bad or api_bad or field_errors or publish_fail:
                data = self._ehoadon_format_error_detail(resp_json, response)
                error = _(
                    'Error when contacting eHoaDon (%(status)s): %(data)s. URL: %(url)s'
                ) % {
                    'status': response.status_code,
                    'data': data,
                    'url': url,
                }
            return resp_json, error
        except (RequestException, ValueError) as err:
            return {
                '_odoo_http': {'url': url, 'method': method, 'status_code': None},
                '_raw_text': str(err)[:2000],
            }, _('Something went wrong, please try again later: %s') % err

    def _ehoadon_token_cache_owner(self, template=None):
        """Template owns token cache when it has API email+password; else config."""
        self.ensure_one()
        if template and template.email and template.password:
            return template
        return self

    def _ehoadon_clear_token_cache(self, template=None):
        """Drop cached JWT so next get_access_token hits Token/Create."""
        self.ensure_one()
        owner = self._ehoadon_token_cache_owner(template=template)
        vals = {
            'access_token': False,
            'access_token_expiry': False,
        }
        if 'refresh_token' in owner._fields:
            vals['refresh_token'] = False
        owner.sudo().write(vals)

    def _ehoadon_is_auth_error(self, resp_json, error=None):
        """True when API rejected Bearer token (401 / invalid|refresh cancelled)."""
        http = (resp_json or {}).get('_odoo_http') or {}
        if http.get('status_code') == 401:
            return True
        chunks = [
            error or '',
            (resp_json or {}).get('message') or '',
            (resp_json or {}).get('_raw_text') or '',
            (resp_json or {}).get('title') or '',
        ]
        text = ' '.join(str(c) for c in chunks).lower()
        return (
            'invalid token' in text
            or 'refresh token' in text
            or 'unauthorized' in text
        )

    def get_access_token(self, template=None, force_refresh=False):
        """Return (access_token, error_message).

        Docs https://docs.ehoadon.online/tao-token :
        POST https://{TaxNumber}.ehoadon.net/Api/Token/Create
        Body PascalCase: TenantId, Email, Password
        TaxNumber = template.tax_number (Mã số thuế cho Endpoint)
        """
        self.ensure_one()
        use_template = bool(template and template.email and template.password)
        cache_owner = self._ehoadon_token_cache_owner(template=template)

        if (
            not force_refresh
            and cache_owner.access_token
            and cache_owner.access_token_expiry
            and cache_owner.access_token_expiry > fields.Datetime.now()
        ):
            return cache_owner.access_token, ''

        email = ((template.email if use_template else self.email) or '').strip()
        password = (template.password if use_template else self.password) or ''
        tax = (
            (template.tax_number if use_template and template.tax_number else self.tax_number)
            or ''
        ).strip()
        tenant_id = (
            (template.tenant_id if use_template and template.tenant_id else self.tenant_id)
            or ''
        ).strip()
        if not email or not password:
            return '', _('Thiếu API Email / API Password trên mẫu eHoaDon.')
        if not tenant_id:
            return '', _('Thiếu Tenant ID trên mẫu eHoaDon.')
        if not tax:
            return '', _(
                'Thiếu Mã số thuế cho Endpoint — dùng để gọi '
                'https://{MST}.ehoadon.net/Api/Token/Create'
            )

        # Host MUST come from tax_number (docs [TaxNumber].ehoadon.net)
        url = 'https://%s.ehoadon.net/Api/Token/Create' % tax
        payload = {
            'TenantId': tenant_id,
            'Email': email,
            'Password': password,
        }

        resp, error = self._ehoadon_send_request(
            method='POST',
            url=url,
            json_data=payload,
            headers={'Content-Type': 'application/json'},
        )
        if error:
            return '', error

        data = resp.get('data') if isinstance(resp.get('data'), dict) else {}
        access_token = (
            (data or {}).get('accessToken')
            or resp.get('accessToken')
            or (data or {}).get('token')
            or resp.get('token')
        )
        # Some APIs return the token string as data
        if not access_token and isinstance(resp.get('data'), str):
            access_token = resp.get('data')
        if not access_token:
            return '', _(
                'eHoaDon không trả accessToken. status=%s message=%s'
            ) % (resp.get('status'), resp.get('message'))

        expired_at = (data or {}).get('accessTokenExpiredAt') or resp.get('accessTokenExpiredAt')
        if expired_at:
            try:
                raw = str(expired_at).replace('Z', '').replace('T', ' ')[:19]
                expiry = fields.Datetime.from_string(raw)
            except Exception:
                expiry = fields.Datetime.now() + timedelta(minutes=30)
        else:
            expiry = fields.Datetime.now() + timedelta(minutes=30)

        vals = {
            'access_token': access_token,
            'access_token_expiry': expiry,
        }
        refresh = (data or {}).get('refreshToken') or resp.get('refreshToken')
        if refresh and hasattr(cache_owner, 'refresh_token'):
            vals['refresh_token'] = refresh

        if use_template:
            template.sudo().write(vals)
        else:
            self.sudo().write(vals)
        return access_token, ''

    def ehoadon_channel(self, template=None):
        """Return 'cash_register' or 'online' based on template flag."""
        self.ensure_one()
        if template and getattr(template, 'is_cash_register', False):
            return 'cash_register'
        return 'online'

    def ehoadon_path(self, resource, template=None, channel=None, **fmt):
        """SSOT path map Online vs CashRegister (Phase 2).

        resource keys: add, update, delete, delete_guid, get, get_guid,
        publish, status, pdf, pdf_guid, xml, xml_guid, business, error_inform, serials
        channel: force 'online' / 'cash_register' instead of the template flag.
        """
        self.ensure_one()
        channel = channel or self.ehoadon_channel(template=template)
        online = {
            'add': 'Api/EInvoiceOnline/AddEInvoice',
            'update': 'Api/EInvoiceOnline/UpdateEInvoice',
            'delete': 'Api/EInvoiceOnline/DeleteEInvoice/%(id)s',
            'delete_guid': 'Api/EInvoiceOnline/DeleteEInvoiceByGuid/%(guid)s',
            'get': 'Api/EInvoiceOnline/GetInvoiceById/%(id)s',
            'get_guid': 'Api/EInvoiceOnline/GetInvoiceByGuid/%(guid)s',
            'publish': 'Api/EInvoiceOnline/PublishInvoice',
            'status': 'Api/EInvoiceOnline/GetStatusInvoices',
            'pdf': 'Api/EInvoiceOnline/DownloadInvoiceAsPdf/%(id)s',
            'pdf_guid': 'Api/EInvoiceOnline/DownloadInvoiceAsPdfByGuid/%(guid)s',
            'xml': 'Api/EInvoiceOnline/DownloadInvoiceAsXml/%(id)s',
            'xml_guid': 'Api/EInvoiceOnline/DownloadInvoiceAsXmlByGuid/%(guid)s',
            'business': 'Api/EInvoiceOnline/InvoiceBusiness',
            'error_inform': 'Api/EInvoiceOnline/SendErrrorInform',
            'serials': 'Api/EInvoiceOnline/GetAvailiableSerial',
        }
        cash = {
            'add': 'Api/CashRegister/AddEInvoice',
            'update': 'Api/CashRegister/UpdateEInvoice',
            'delete': 'Api/CashRegister/DeleteEInvoice/%(id)s',
            'delete_guid': 'Api/CashRegister/DeleteEInvoiceByGuid/%(guid)s',
            'get': 'Api/CashRegister/GetEInvoiceById/%(id)s',
            'get_guid': 'Api/CashRegister/GetEInvoiceByGuid/%(guid)s',
            'publish': 'Api/CashRegister/SendToTaxAuthority',
            'status': 'Api/CashRegister/GetStatusInvoices',
            'pdf': 'Api/CashRegister/DownloadEInvoiceAsPdf/%(id)s',
            'pdf_guid': 'Api/CashRegister/DownloadEInvoiceAsPdfByGuid/%(guid)s',
            'xml': 'Api/CashRegister/DownloadEInvoiceAsXml/%(id)s',
            'xml_guid': 'Api/CashRegister/DownloadEInvoiceAsXmlByGuid/%(guid)s',
            'business': 'Api/CashRegister/InvoiceBusiness',
            # SendErrorInform only documented on Online — still call Online for cancel.
            'error_inform': 'Api/EInvoiceOnline/SendErrrorInform',
            'serials': 'Api/EInvoiceOnline/GetAvailiableSerial',
        }
        table = cash if channel == 'cash_register' else online
        if resource not in table:
            raise UserError(_('Unknown eHoaDon resource: %s') % resource)
        path = table[resource]
        if fmt:
            path = path % fmt
        return path

    def api_call(self, method, path, *, json_data=None, template=None, token=None):
        """Authenticated API call. Returns (resp_json, error).

        On 401 / invalid token: clear cache, Token/Create once, retry once
        (unless caller already passed an explicit token).
        """
        self.ensure_one()
        explicit_token = bool(token)
        if not token:
            token, error = self.get_access_token(template=template)
            if error:
                return {}, error
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token,
        }
        url = self.api_url(path, template=template)
        resp, error = self._ehoadon_send_request(
            method=method,
            url=url,
            json_data=json_data,
            headers=headers,
        )
        if error and not explicit_token and self._ehoadon_is_auth_error(resp, error):
            self._ehoadon_clear_token_cache(template=template)
            token, refresh_err = self.get_access_token(
                template=template, force_refresh=True,
            )
            if refresh_err:
                return resp or {}, refresh_err
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer %s' % token,
            }
            resp, error = self._ehoadon_send_request(
                method=method,
                url=url,
                json_data=json_data,
                headers=headers,
            )
        return resp, error
