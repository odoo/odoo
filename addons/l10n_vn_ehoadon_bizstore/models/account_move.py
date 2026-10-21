# -*- coding: utf-8 -*-
import base64
import json
import re

from markupsafe import Markup

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError

from .ehoadon_payload_builder import (
    BUSINESS_TYPE_MAP,
    EhoadonPayloadBuilder,
    STATUS_NEW,
)


class AccountMove(models.Model):
    _inherit = 'account.move'

    _BUYER_CONSUMER_LABEL = 'Bán cho người tiêu dùng'
    _BUYER_DEFAULT_NAME = 'Người mua không cung cấp thông tin'
    _BUYER_DEFAULT_LEGAL_NAME = 'Người mua không lấy hóa đơn'
    _BUYER_DEFAULT_ADDRESS = 'Người mua không cung cấp địa chỉ'

    ehoadon_template_id = fields.Many2one(
        'ehoadon.template',
        string='eHoaDon Template',
        help='If empty, uses default template from eHoaDon config.',
    )
    ehoadon_issue_date = fields.Datetime(string='eHoaDon Issue Date', copy=False)
    ehoadon_invoice_state = fields.Selection(
        selection=[
            ('ready_to_send', 'Ready to send'),
            ('draft_remote', 'Draft on eHoaDon'),
            ('sent', 'Sent'),
            ('canceled', 'Canceled / Error inform'),
            ('adjusted', 'Adjusted'),
            ('replaced', 'Replaced'),
            ('error', 'Error'),
        ],
        string='eHoaDon State',
        copy=False,
        default='ready_to_send',
    )
    ehoadon_invoice_id = fields.Char(string='eHoaDon Invoice Id', copy=False, readonly=True)
    ehoadon_guid = fields.Char(string='eHoaDon GUID', copy=False, readonly=True)
    ehoadon_lookup_code = fields.Char(string='eHoaDon Lookup Code', copy=False, readonly=True)
    ehoadon_view_url = fields.Char(string='eHoaDon View URL', copy=False, readonly=True)
    ehoadon_invoice_number = fields.Char(string='eHoaDon Invoice Number', copy=False, readonly=True)
    ehoadon_remote_status = fields.Char(
        string='eHoaDon remote status',
        copy=False,
        readonly=True,
        help='Last value from GetInvoiceById / GetStatusInvoices.',
    )
    ehoadon_business_type = fields.Selection(
        # Mirror vms_sinvoice: UI only offers replacement; empty = phát hành thường.
        selection=[
            ('replace', 'Hóa đơn thay thế'),
        ],
        string='Loại nghiệp vụ eHoaDon',
        copy=False,
    )
    ehoadon_origin_move_id = fields.Many2one(
        'account.move',
        string='Hóa đơn gốc eHoaDon',
        copy=False,
        # Mirror vms_sinvoice: only invoices that already have an eHoaDon number.
        domain="[('ehoadon_invoice_number', '!=', False), ('ehoadon_invoice_number', '!=', '')]",
        help='Original posted invoice for InvoiceBusiness (adjust/replace).',
    )
    ehoadon_cancel_note = fields.Text(
        string='eHoaDon cancel / error note',
        copy=False,
    )
    ehoadon_log_ids = fields.One2many('ehoadon.invoice.log', 'move_id', string='eHoaDon API Logs')
    ehoadon_log_json = fields.Html(string='eHoaDon API Log', compute='_compute_ehoadon_log_json')
    ehoadon_json_attachment_id = fields.Many2one('ir.attachment', string='eHoaDon JSON', copy=False)

    @api.depends(
        'ehoadon_log_ids',
        'ehoadon_log_ids.date',
        'ehoadon_log_ids.operation',
        'ehoadon_log_ids.status',
        'ehoadon_log_ids.message',
        'ehoadon_log_ids.payload',
    )
    def _compute_ehoadon_log_json(self):
        """Show full request/response JSON on the invoice (no Preview click needed)."""
        Log = self.env['ehoadon.invoice.log'].sudo()
        for move in self:
            logs = Log.search(
                [('move_id', '=', move.id)],
                order='date desc, id desc',
                limit=30,
            )
            if not logs:
                move.ehoadon_log_json = False
                continue
            entries = []
            for log in logs:
                payload_value = ''
                if log.payload:
                    try:
                        payload_value = json.loads(log.payload)
                    except (TypeError, ValueError):
                        payload_value = log.payload
                entries.append({
                    'date': fields.Datetime.context_timestamp(
                        move, log.date
                    ).strftime('%Y-%m-%d %H:%M:%S') if log.date else '',
                    'operation': log.operation,
                    'status': log.status,
                    'message': log.message,
                    'payload': payload_value,
                })
            json_text = json.dumps(entries, ensure_ascii=False, indent=2, default=str)
            move.ehoadon_log_json = Markup(
                '<pre class="o_ehoadon_json_pre" style="white-space:pre-wrap;'
                'max-height:480px;overflow:auto;">{}</pre>'
            ).format(Markup.escape(json_text))

    # ------------------------------------------------------------------
    # Config / template / helpers
    # ------------------------------------------------------------------

    def _ehoadon_config(self):
        return self.env['ehoadon.config'].get_ehoadon_config()

    def _ehoadon_resolve_template(self):
        self.ensure_one()
        template = self.ehoadon_template_id
        if not template:
            config = self._ehoadon_config()
            template = config.default_template_id
            if template:
                try:
                    self.ehoadon_template_id = template
                except Exception:
                    pass
        if not template:
            raise UserError(_(
                'Không có mẫu eHoaDon. Đặt mẫu mặc định trong Cấu hình eHoaDon '
                'hoặc chọn mẫu trên hóa đơn.'
            ))
        return template

    def _ehoadon_format_date(self, dt):
        if not dt:
            dt = fields.Datetime.now()
        if isinstance(dt, str):
            return dt
        return fields.Datetime.to_string(dt).replace(' ', 'T') + 'Z'

    def _ehoadon_is_product_line(self, line):
        return (not getattr(line, 'display_type', False)) or getattr(line, 'display_type', False) == 'product'

    def _ehoadon_consumer_customer(self):
        return {
            'taxNumber': '',
            'companyName': self._BUYER_CONSUMER_LABEL,
            'fullName': self._BUYER_CONSUMER_LABEL,
            'address': '',
            'email': '',
            'phoneNumber': '',
        }

    _EINVOICE_FIELDS = (
        'einvoice_vat_info',
        'einvoice_vat',
        'einvoice_name',
        'einvoice_buyer_name',
        'einvoice_partner_id',
        'einvoice_address',
    )

    def _ehoadon_einvoice_value(self, partner, field_name):
        return (partner[field_name] or '').strip()

    def _ehoadon_einvoice_customer(self, partner):
        return {
            'taxNumber': self._ehoadon_einvoice_value(partner, 'einvoice_vat'),
            'companyName': self._ehoadon_einvoice_value(partner, 'einvoice_name') or self._BUYER_DEFAULT_NAME,
            'fullName': (
                self._ehoadon_einvoice_value(partner, 'einvoice_buyer_name')
                or self._BUYER_DEFAULT_LEGAL_NAME
            ),
            'address': self._ehoadon_einvoice_value(partner, 'einvoice_address') or self._BUYER_DEFAULT_ADDRESS,
            'email': '',
            'phoneNumber': '',
        }

    @staticmethod
    def _ehoadon_valid_tax_number(value):
        """MST VN: 10 số, 10 số + '-' + 3 số (chi nhánh), hoặc 12 số (CCCD)."""
        return bool(re.fullmatch(r'\d{10}(-\d{3})?|\d{12}', (value or '').strip()))

    def _ehoadon_build_invoice_customer(self):
        """Map buyer → eHoaDon invoiceCustomer.

        Tab «Thông tin xuất hóa đơn» on the partner wins; otherwise standard
        partner data, and a partner without tax code is a retail consumer.
        """
        self.ensure_one()
        partner = self.commercial_partner_id or self.partner_id
        if any(self._ehoadon_einvoice_value(partner, f) for f in self._EINVOICE_FIELDS):
            return self._ehoadon_einvoice_customer(partner)
        tax_number = (partner.vat or '').strip()
        # VAT chuẩn của Odoo chỉ dùng khi đúng định dạng MST Việt Nam;
        # VAT nước ngoài (vd US12345673) hoặc rỗng → bán cho người tiêu dùng.
        if not tax_number or not self._ehoadon_valid_tax_number(tax_number):
            return self._ehoadon_consumer_customer()
        address_lines = (partner._display_address(without_name=True) or '').splitlines()
        address = ', '.join(line.strip() for line in address_lines if line.strip())
        return {
            'taxNumber': tax_number,
            'companyName': partner.name or self._BUYER_DEFAULT_NAME,
            'fullName': self.partner_id.name or partner.name or self._BUYER_DEFAULT_LEGAL_NAME,
            'address': address or self._BUYER_DEFAULT_ADDRESS,
            'email': '',
            'phoneNumber': '',
        }

    def _ehoadon_generate_payload(self, status=STATUS_NEW, include_remote_ids=False):
        self.ensure_one()
        return EhoadonPayloadBuilder(self).build(
            status=status, include_remote_ids=include_remote_ids,
        )

    def _ehoadon_pick(self, data, *keys):
        data = data or {}
        for key in keys:
            val = data.get(key)
            if val not in (None, False, ''):
                return val
        return False

    def _ehoadon_notify(self, message, title=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title or _('Thành công'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def _ehoadon_path(self, resource, template=None, **fmt):
        config = self._ehoadon_config()
        template = template or self._ehoadon_resolve_template()
        return config.ehoadon_path(resource, template=template, **fmt)
    def _ehoadon_origin_remote_id(self):
        self.ensure_one()
        origin = self.ehoadon_origin_move_id
        if not origin or not origin.ehoadon_invoice_id:
            raise UserError(_(
                'Chọn hóa đơn gốc (eHoaDon origin) đã có invoiceId trước khi điều chỉnh/thay thế.'
            ))
        return origin.ehoadon_invoice_id

    def _ehoadon_should_use_business(self):
        self.ensure_one()
        btype = self.ehoadon_business_type or 'normal'
        if btype != 'normal':
            return True
        return self.move_type == 'out_refund' and bool(self.ehoadon_origin_move_id)

    def _ehoadon_commit(self):
        """Persist API logs/state even when UserError rolls back the request.

        Mirror vms_sinvoice._sinvoice_commit — without this, Publish/send errors
        never appear on tab «eHoaDon API Log».
        """
        self.ensure_one()
        if self.env.context.get('ehoadon_skip_commit'):
            return
        try:
            from odoo.tools import config
            if config.get('test_enable'):
                return
        except Exception:
            pass
        try:
            can_commit = getattr(self, '_can_commit', None)
            if callable(can_commit) and not can_commit():
                return
            self._cr.commit()
        except Exception:
            return

    def _ehoadon_sanitize_response(self, resp_json):
        if not isinstance(resp_json, dict):
            return resp_json
        data = dict(resp_json)
        inner = data.get('data')
        if isinstance(inner, dict):
            for key in ('fileContent', 'FileContent'):
                if inner.get(key):
                    inner = dict(inner)
                    inner[key] = '<base64 omitted len=%s>' % len(inner.get(key) or '')
                    data['data'] = inner
                    break
        return data

    def _ehoadon_log_exchange(self, operation, status, message, *, request=None, response=None, extra=None):
        """Always log full outbound request + inbound response for invoice troubleshooting."""
        self.ensure_one()
        body = {
            'request': request,
            'response': self._ehoadon_sanitize_response(response) if response is not None else None,
        }
        if extra:
            body.update(extra)
        return self._ehoadon_create_log(operation, status, message, body)

    def _ehoadon_create_log(self, operation, status, message='', payload=None):
        self.ensure_one()
        log = self.env['ehoadon.invoice.log'].sudo().create({
            'move_id': self.id,
            'operation': operation,
            'status': status,
            'message': message,
        })
        if payload is not None:
            log.set_payload_from_dict(payload)
        # Force recompute so tab "eHoaDon API Log" shows body without Preview click.
        self._compute_ehoadon_log_json()
        # Commit so UserError / rollback does not wipe the log row.
        self._ehoadon_commit()
        return log

    def _ehoadon_store_json_attachment(self, payload):
        """Không còn lưu payload JSON thành attachment.

        Payload gửi eHoaDon đã nằm trong tab «eHoaDon API Log» (request của mỗi lần gọi API),
        nên không tạo thêm file đính kèm vào DB. Giữ hàm để các chỗ gọi không phải sửa.
        """
        self.ensure_one()
        return False

    def _ehoadon_check_configuration(self):
        self.ensure_one()
        errors = []
        try:
            config = self._ehoadon_config()
        except UserError as err:
            return [str(err)]
        template = self.ehoadon_template_id or config.default_template_id
        email = (template and template.email) or config.email
        password = (template and template.password) or config.password
        if not email or not password:
            errors.append(_('Thiếu email/mật khẩu API eHoaDon.'))
        try:
            tmpl = self._ehoadon_resolve_template()
            if not tmpl.serial:
                errors.append(_('Mẫu eHoaDon thiếu serial (ký hiệu).'))
        except UserError as err:
            errors.append(str(err))
        for line in self.invoice_line_ids.filtered(self._ehoadon_is_product_line):
            if not line.tax_ids:
                continue
            percent = line.tax_ids.filtered(lambda t: t.amount_type == 'percent')
            if len(percent) > 1:
                errors.append(_(
                    'eHoaDon Phase 1 chỉ hỗ trợ một thuế %% trên mỗi dòng. Dòng: %s'
                ) % (line.name or line.display_name))
                break
        return errors

    def _ehoadon_apply_add_result(self, data, state):
        self.ensure_one()
        data = data or {}
        vals = {
            'ehoadon_invoice_id': self._ehoadon_pick(data, 'invoiceId', 'InvoiceId') or self.ehoadon_invoice_id,
            'ehoadon_guid': self._ehoadon_pick(data, 'guid', 'Guid') or self.ehoadon_guid,
            'ehoadon_lookup_code': self._ehoadon_pick(data, 'lookupCode', 'LookupCode') or self.ehoadon_lookup_code,
            'ehoadon_view_url': self._ehoadon_pick(data, 'viewUrl', 'ViewUrl') or self.ehoadon_view_url,
            'ehoadon_invoice_state': state,
        }
        detail = data.get('invoiceDetail') or data.get('InvoiceDetail') or {}
        number = self._ehoadon_pick(detail, 'invoiceNumber', 'InvoiceNumber')
        if number:
            vals['ehoadon_invoice_number'] = number
        self.write(vals)

    # ------------------------------------------------------------------
    # Actions Phase 1 + Phase 2
    # ------------------------------------------------------------------

    def _ehoadon_ensure_invoice_id_for_pdf(self, template):
        """Ensure the remote invoice exists and matches Odoo before DownloadInvoiceAsPdf/{id}.

        Docs: https://docs.ehoadon.online/download-invoice-as-pdf
        eHoaDon has no stateless preview: the PDF comes from a stored invoice. An unissued
        draft is refreshed (UpdateEInvoice) so the PDF follows line/template changes;
        if the draft lives on the other channel it is deleted and re-added.
        Issued invoices and business (adjust/replace) drafts are never touched —
        UpdateEInvoice resets a business draft to a normal invoice.
        """
        self.ensure_one()
        business = self._ehoadon_should_use_business()
        if self.ehoadon_invoice_id and (business or not self._ehoadon_is_unissued_draft()):
            return self.ehoadon_invoice_id
        if business:
            raise UserError(_(
                'Điều chỉnh/thay thế: dùng «eHoaDon: Phát hành» trước, rồi xem PDF.'
            ))
        if self.ehoadon_invoice_id:
            if not self._ehoadon_update_remote_draft(template):
                return self.ehoadon_invoice_id
            self._ehoadon_drop_remote_draft(template)
        config = self._ehoadon_config()
        payload = self._ehoadon_generate_payload(status=STATUS_NEW)
        self._ehoadon_store_json_attachment(payload)
        path = config.ehoadon_path('add', template=template)
        resp, error = config.api_call('POST', path, json_data=payload, template=template)
        if error:
            self.ehoadon_invoice_state = 'error'
            self._ehoadon_log_exchange(
                'create_draft', 'error', error, request=payload, response=resp,
            )
            raise UserError(error)
        data = resp.get('data') or {}
        field_errors = data.get('Errors') or data.get('errors')
        if field_errors:
            msg = _('eHoaDon trả lỗi field: %s') % field_errors
            self.ehoadon_invoice_state = 'error'
            self._ehoadon_log_exchange(
                'create_draft', 'error', msg, request=payload, response=resp,
            )
            raise UserError(msg)
        # Keep draft_remote unless already issued
        state = self.ehoadon_invoice_state
        if state not in ('sent', 'canceled', 'adjusted', 'replaced'):
            state = 'draft_remote'
        self._ehoadon_apply_add_result(data, state)
        invoice_id = self.ehoadon_invoice_id or self._ehoadon_pick(data, 'invoiceId', 'InvoiceId')
        if not invoice_id:
            raise UserError(_('eHoaDon không trả invoiceId — không gọi được DownloadInvoiceAsPdf.'))
        self._ehoadon_log_exchange(
            'create_draft', 'success', _('AddEInvoice OK (cần id để Download PDF).'),
            request=payload, response=resp,
        )
        return invoice_id

    def _ehoadon_fetch_file_content(self, kind='pdf'):
        """Gọi API eHoaDon lấy PDF/XML, trả (bytes, tên_file, mimetype). KHÔNG lưu DB.

        PDF path = POST Api/EInvoiceOnline/DownloadInvoiceAsPdf/{id}
        (docs.ehoadon.online/download-invoice-as-pdf).
        """
        self.ensure_one()
        if not self.ehoadon_invoice_id and not self.ehoadon_guid:
            raise UserError(_('Chưa có invoiceId/guid eHoaDon.'))
        template = self._ehoadon_resolve_template()
        config = self._ehoadon_config()
        if kind == 'pdf':
            resource = 'pdf' if self.ehoadon_invoice_id else 'pdf_guid'
            mimetype = 'application/pdf'
            default_ext = 'pdf'
            op = 'download_pdf'
        elif kind == 'xml':
            resource = 'xml' if self.ehoadon_invoice_id else 'xml_guid'
            mimetype = 'application/xml'
            default_ext = 'xml'
            op = 'download_xml'
        else:
            raise UserError(_('Loại file eHoaDon không hỗ trợ: %s') % kind)
        fmt = {'id': self.ehoadon_invoice_id} if self.ehoadon_invoice_id else {'guid': self.ehoadon_guid}
        path = config.ehoadon_path(resource, template=template, **fmt)
        resp, error = config.api_call('POST', path, template=template)
        if error:
            self._ehoadon_log_exchange(
                op, 'error', error, request={'path': path}, response=resp,
            )
            raise UserError(error)
        data = resp.get('data') or {}
        content_b64 = self._ehoadon_pick(data, 'fileContent', 'FileContent')
        if not content_b64:
            raise UserError(_('eHoaDon không trả FileContent/fileContent %s.') % kind.upper())
        file_name = self._ehoadon_pick(data, 'fileName', 'FileName') or (
            '%s_ehoadon.%s' % ((self.name or 'invoice').replace('/', '_'), default_ext)
        )
        try:
            raw = base64.b64decode(content_b64)
        except Exception:
            raw = content_b64.encode() if isinstance(content_b64, str) else bytes(content_b64)
        if not raw:
            raise UserError(_('eHoaDon trả file %s rỗng.') % kind.upper())
        self._ehoadon_log_exchange(
            op, 'success', _('%s via DownloadInvoiceAs%s.') % (kind.upper(), kind.capitalize()),
            request={'path': path, 'id': self.ehoadon_invoice_id or self.ehoadon_guid},
            response=self._ehoadon_sanitize_response(resp),
            extra={'fileName': file_name},
        )
        return raw, file_name, mimetype

    def _ehoadon_fetch_file_attachment(self, kind='pdf'):
        """Như _ehoadon_fetch_file_content nhưng lưu thành ir.attachment (dùng cho nút Tải về)."""
        self.ensure_one()
        raw, file_name, mimetype = self._ehoadon_fetch_file_content(kind)
        att = self.env['ir.attachment'].with_user(SUPERUSER_ID).create({
            'name': file_name,
            'type': 'binary',
            'raw': raw,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': mimetype,
        })
        if not att.file_size:
            raise UserError(_('Không lưu được nội dung file %s vào attachment.') % kind.upper())
        return att

    def action_ehoadon_preview_invoice(self):
        """Xem trước = DownloadInvoiceAsPdf/{id} (mở PDF tab).

        Docs: https://docs.ehoadon.online/download-invoice-as-pdf
        Chưa có id → AddEInvoice một lần để lấy id, rồi chỉ gọi Download PDF.
        """
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_preview'):
            raise UserError(_('Bạn không có quyền xem trước eHoaDon.'))
        errors = self._ehoadon_check_configuration()
        if errors:
            raise UserError('\n'.join(errors))
        template = self._ehoadon_resolve_template()
        self._ehoadon_ensure_invoice_id_for_pdf(template)
        self._ehoadon_create_log(
            'preview', 'success',
            _('Xem trước qua DownloadInvoiceAsPdf (không lưu file vào DB).'),
            {
                'endpoint': 'Api/EInvoiceOnline/DownloadInvoiceAsPdf/%s' % self.ehoadon_invoice_id,
                'invoiceId': self.ehoadon_invoice_id,
            },
        )
        return {
            'type': 'ir.actions.act_url',
            'url': '/ehoadon/preview/%s' % self.id,
            'target': 'new',
        }

    def action_ehoadon_preview_payload(self):
        """Alias → DownloadInvoiceAsPdf preview."""
        return self.action_ehoadon_preview_invoice()

    def action_ehoadon_create_draft(self):
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_create_draft'):
            raise UserError(_('Bạn không có quyền tạo nháp eHoaDon.'))
        if self.state != 'posted':
            raise UserError(_('Chỉ tạo nháp khi hóa đơn đã posted.'))
        if self.ehoadon_invoice_state in ('sent', 'canceled', 'adjusted', 'replaced'):
            raise UserError(_('Hóa đơn đã phát hành / khóa trên eHoaDon.'))
        errors = self._ehoadon_check_configuration()
        if errors:
            raise UserError('\n'.join(errors))
        template = self._ehoadon_resolve_template()
        self._ehoadon_ensure_invoice_id_for_pdf(template)
        self.message_post(body=_('Đã tạo hóa đơn nháp eHoaDon (id=%s).') % (
            self.ehoadon_invoice_id or ''
        ))
        return self._ehoadon_notify(_('Đã tạo nháp eHoaDon.'))

    def _ehoadon_add_or_business(self, template, operation='send'):
        """POST AddEInvoice or InvoiceBusiness. Returns (invoice_id, resp)."""
        config = self._ehoadon_config()
        if self._ehoadon_should_use_business():
            btype = self.ehoadon_business_type or 'normal'
            if btype == 'normal':
                btype = 'adjusted_down'
            if btype == 'replace' and not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_send_replacement'):
                raise UserError(_('Bạn không có quyền phát hành hóa đơn thay thế.'))
            invoice_type = BUSINESS_TYPE_MAP.get(btype)
            if invoice_type is None:
                raise UserError(_('Loại nghiệp vụ eHoaDon không hợp lệ: %s') % btype)
            origin_id = self._ehoadon_origin_remote_id()
            payload = EhoadonPayloadBuilder(self).build_business(invoice_type, origin_id, status=STATUS_NEW)
            path = config.ehoadon_path('business', template=template)
        else:
            payload = self._ehoadon_generate_payload(status=STATUS_NEW)
            path = config.ehoadon_path('add', template=template)

        store = payload.get('invoice') if isinstance(payload, dict) and 'invoice' in payload else payload
        self._ehoadon_store_json_attachment(store)
        resp, error = config.api_call('POST', path, json_data=payload, template=template)
        if error:
            self.ehoadon_invoice_state = 'error'
            self._ehoadon_log_exchange(
                operation, 'error', error, request=payload, response=resp,
            )
            raise UserError(error)
        data = resp.get('data') or {}
        field_errors = data.get('Errors') or data.get('errors')
        if field_errors:
            msg = _('eHoaDon trả lỗi field: %s') % field_errors
            self.ehoadon_invoice_state = 'error'
            self._ehoadon_log_exchange(
                operation, 'error', msg, request=payload, response=resp,
            )
            raise UserError(msg)

        state = 'draft_remote'
        if self._ehoadon_should_use_business():
            btype = self.ehoadon_business_type or 'adjusted_down'
            state = 'replaced' if btype == 'replace' else 'adjusted'
        self._ehoadon_apply_add_result(data, state)
        invoice_id = self._ehoadon_pick(data, 'invoiceId', 'InvoiceId')
        if not invoice_id:
            msg = _('eHoaDon không trả invoiceId.')
            self.ehoadon_invoice_state = 'error'
            self._ehoadon_log_exchange(
                operation, 'error', msg, request=payload, response=resp,
            )
            raise UserError(msg)
        self._ehoadon_log_exchange(
            operation, 'success', _('Add/Business OK.'),
            request=payload, response=resp,
        )
        return invoice_id, resp

    def action_ehoadon_send_invoice(self):
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_send_invoice'):
            raise UserError(_('Bạn không có quyền phát hành eHoaDon.'))
        if self.state != 'posted':
            raise UserError(_('Thanh toán / post hóa đơn trước khi xuất eHoaDon.'))
        if self.ehoadon_invoice_state in ('sent', 'canceled', 'adjusted', 'replaced'):
            raise UserError(_('Hóa đơn đã phát hành / khóa trên eHoaDon.'))
        errors = self._ehoadon_check_configuration()
        if errors:
            raise UserError('\n'.join(errors))

        template = self._ehoadon_resolve_template()
        config = self._ehoadon_config()
        invoice_id = self.ehoadon_invoice_id
        business_done = False

        if self._ehoadon_should_use_business():
            invoice_id, _resp = self._ehoadon_add_or_business(template, operation='send')
            business_done = True
        elif not invoice_id:
            invoice_id, _resp = self._ehoadon_add_or_business(template, operation='send')

        if business_done:
            self.message_post(body=_('Đã gửi InvoiceBusiness eHoaDon (id=%s).') % invoice_id)
            return self._ehoadon_notify(_('Đã gửi InvoiceBusiness eHoaDon.'))

        pub_path = config.ehoadon_path('publish', template=template)
        pub_resp, pub_error = config.api_call(
            'POST',
            pub_path,
            json_data={'invoiceIds': [invoice_id]},
            template=template,
        )
        if pub_error:
            self.ehoadon_invoice_state = 'error'
            self._ehoadon_log_exchange(
                'send', 'error', pub_error,
                request={
                    'path': pub_path,
                    'invoiceIds': [invoice_id],
                },
                response=pub_resp,
            )
            raise UserError(pub_error)
        self.ehoadon_invoice_state = 'sent'
        self._ehoadon_log_exchange(
            'send', 'success', _('Đã phát hành eHoaDon.'),
            request={'invoiceIds': [invoice_id]}, response=pub_resp,
        )
        self.message_post(body=_('Đã phát hành hóa đơn eHoaDon (id=%s).') % invoice_id)
        return self._ehoadon_notify(_('Đã phát hành eHoaDon.'))

    def action_ehoadon_update_draft(self):
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_create_draft'):
            raise UserError(_('Bạn không có quyền cập nhật nháp eHoaDon.'))
        if self.ehoadon_invoice_state != 'draft_remote' or not self.ehoadon_invoice_id:
            raise UserError(_('Chỉ cập nhật khi còn nháp remote (có invoiceId).'))
        errors = self._ehoadon_check_configuration()
        if errors:
            raise UserError('\n'.join(errors))
        template = self._ehoadon_resolve_template()
        error = self._ehoadon_update_remote_draft(template)
        if error:
            self.ehoadon_invoice_state = 'error'
            raise UserError(error)
        return self._ehoadon_notify(_('Đã cập nhật nháp eHoaDon.'))

    def _ehoadon_update_remote_draft(self, template):
        """UpdateEInvoice with current Odoo data. Returns error message ('' on success)."""
        self.ensure_one()
        payload = self._ehoadon_generate_payload(status=STATUS_NEW, include_remote_ids=True)
        self._ehoadon_store_json_attachment(payload)
        config = self._ehoadon_config()
        path = config.ehoadon_path('update', template=template)
        resp, error = config.api_call('POST', path, json_data=payload, template=template)
        data = (resp or {}).get('data') or {}
        field_errors = not error and (data.get('Errors') or data.get('errors'))
        if field_errors:
            error = _('eHoaDon trả lỗi field: %s') % field_errors
        if error:
            self._ehoadon_log_exchange(
                'update', 'error', error, request=payload, response=resp,
            )
            return error
        self._ehoadon_apply_add_result(data, 'draft_remote')
        self._ehoadon_log_exchange(
            'update', 'success', _('Đã cập nhật nháp eHoaDon.'),
            request=payload, response=resp,
        )
        return ''

    def _ehoadon_is_unissued_draft(self):
        """Remote draft never published: no real invoice number yet."""
        self.ensure_one()
        number = (self.ehoadon_invoice_number or '').strip('0')
        return (
            bool(self.ehoadon_invoice_id)
            and self.ehoadon_invoice_state in ('draft_remote', 'error')
            and not number
        )

    def _ehoadon_forget_remote_ids(self):
        self.write({
            'ehoadon_invoice_id': False,
            'ehoadon_guid': False,
            'ehoadon_lookup_code': False,
            'ehoadon_view_url': False,
            'ehoadon_invoice_number': False,
            'ehoadon_invoice_state': 'ready_to_send',
            'ehoadon_remote_status': False,
        })

    def _ehoadon_drop_remote_draft(self, template):
        """Delete a stale draft on whichever channel holds it, then forget its ids.

        The template channel may have changed since the draft was created
        (CashRegister vs EInvoiceOnline only see their own invoices).
        """
        self.ensure_one()
        config = self._ehoadon_config()
        current = config.ehoadon_channel(template=template)
        other = 'online' if current == 'cash_register' else 'cash_register'
        for channel in (current, other):
            path = config.ehoadon_path(
                'delete', template=template, channel=channel, id=self.ehoadon_invoice_id,
            )
            resp, error = config.api_call('DELETE', path, template=template)
            self._ehoadon_log_exchange(
                'delete', 'error' if error else 'success',
                error or _('Đã xóa nháp eHoaDon.'),
                request={'path': path}, response=resp,
            )
            if not error:
                break
        self._ehoadon_forget_remote_ids()

    def action_ehoadon_delete_draft(self):
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_create_draft'):
            raise UserError(_('Bạn không có quyền xóa nháp eHoaDon.'))
        if self.ehoadon_invoice_state != 'draft_remote':
            raise UserError(_('Chỉ xóa nháp remote (chưa phát hành).'))
        if not self.ehoadon_invoice_id and not self.ehoadon_guid:
            raise UserError(_('Thiếu invoiceId/guid để xóa.'))
        template = self._ehoadon_resolve_template()
        config = self._ehoadon_config()
        if self.ehoadon_invoice_id:
            path = config.ehoadon_path('delete', template=template, id=self.ehoadon_invoice_id)
        else:
            path = config.ehoadon_path(
                'delete_guid', template=template, guid=self.ehoadon_guid,
            )
        resp, error = config.api_call('DELETE', path, template=template)
        if error:
            self._ehoadon_log_exchange(
                'delete', 'error', error, request={'path': path}, response=resp,
            )
            raise UserError(error)
        self._ehoadon_forget_remote_ids()
        self._ehoadon_log_exchange(
            'delete', 'success', _('Đã xóa nháp eHoaDon.'),
            request={'path': path}, response=resp,
        )
        return self._ehoadon_notify(_('Đã xóa nháp eHoaDon.'))

    def action_ehoadon_refresh_status(self):
        self.ensure_one()
        if not self.ehoadon_invoice_id and not self.ehoadon_guid:
            raise UserError(_('Chưa có invoiceId/guid eHoaDon.'))
        template = self._ehoadon_resolve_template()
        config = self._ehoadon_config()
        if self.ehoadon_invoice_id:
            path = config.ehoadon_path('get', template=template, id=self.ehoadon_invoice_id)
        else:
            path = config.ehoadon_path(
                'get_guid', template=template, guid=self.ehoadon_guid,
            )
        resp, error = config.api_call('GET', path, template=template)
        if error:
            self._ehoadon_log_exchange(
                'status', 'error', error, request={'path': path}, response=resp,
            )
            raise UserError(error)
        data = resp.get('data') or {}
        status_val = False
        if isinstance(data, dict):
            status_val = self._ehoadon_pick(
                data, 'status', 'Status', 'invoiceStatus', 'InvoiceStatus',
            )
            self._ehoadon_apply_add_result(data, self.ehoadon_invoice_state or 'sent')
        if not status_val and self.ehoadon_invoice_id:
            st_path = config.ehoadon_path('status', template=template)
            st_resp, st_error = config.api_call(
                'POST', st_path,
                json_data={'invoiceIds': [self.ehoadon_invoice_id]},
                template=template,
            )
            if not st_error:
                resp = st_resp
                st_data = st_resp.get('data')
                if isinstance(st_data, list) and st_data:
                    status_val = self._ehoadon_pick(
                        st_data[0], 'status', 'Status', 'invoiceStatus',
                    )
                elif isinstance(st_data, dict):
                    status_val = self._ehoadon_pick(
                        st_data, 'status', 'Status', 'invoiceStatus',
                    )
        if status_val not in (None, False, ''):
            self.ehoadon_remote_status = str(status_val)
        self._ehoadon_log_exchange(
            'status', 'success', _('Đã làm mới trạng thái eHoaDon.'),
            request={'path': path}, response=resp,
        )
        return self._ehoadon_notify(_('Đã làm mới trạng thái eHoaDon.'))

    def action_ehoadon_send_error_inform(self):
        """SendErrrorInform — thông báo sai sót / hủy nghiệp vụ sau phát hành."""
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_send_invoice'):
            raise UserError(_('Bạn không có quyền gửi thông báo sai sót eHoaDon.'))
        if self.ehoadon_invoice_state not in ('sent', 'adjusted', 'replaced', 'error'):
            raise UserError(_('Chỉ gửi thông báo sai sót khi HĐ đã có trên eHoaDon (sent).'))
        if not self.ehoadon_invoice_id:
            raise UserError(_('Thiếu invoiceId eHoaDon.'))
        note = (self.ehoadon_cancel_note or '').strip()
        if not note:
            raise UserError(_('Nhập lý do vào ô «eHoaDon cancel / error note» trước.'))
        template = self._ehoadon_resolve_template()
        config = self._ehoadon_config()
        payload = EhoadonPayloadBuilder(self).build_error_inform(description=note)
        path = config.ehoadon_path('error_inform', template=template)
        resp, error = config.api_call('POST', path, json_data=payload, template=template)
        if error:
            self._ehoadon_log_exchange(
                'error_inform', 'error', error, request=payload, response=resp,
            )
            raise UserError(error)
        self.ehoadon_invoice_state = 'canceled'
        self._ehoadon_log_exchange(
            'error_inform', 'success', _('Đã gửi thông báo sai sót eHoaDon.'),
            request=payload, response=resp,
        )
        self.message_post(body=_('eHoaDon SendErrrorInform: %s') % note)
        return self._ehoadon_notify(_('Đã gửi thông báo sai sót eHoaDon.'))

    def action_ehoadon_download_pdf(self):
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_send_invoice'):
            raise UserError(_('Bạn không có quyền tải PDF eHoaDon.'))
        if not self.ehoadon_invoice_id and not self.ehoadon_guid:
            raise UserError(_('Chưa có invoiceId/guid eHoaDon — hãy xem trước hoặc phát hành trước.'))
        att = self._ehoadon_fetch_file_attachment(kind='pdf')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % att.id,
            'target': 'self',
        }

    def action_ehoadon_download_xml(self):
        self.ensure_one()
        if not self.env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_send_invoice'):
            raise UserError(_('Bạn không có quyền tải XML eHoaDon.'))
        if not self.ehoadon_invoice_id and not self.ehoadon_guid:
            raise UserError(_('Chưa có invoiceId/guid eHoaDon.'))
        att = self._ehoadon_fetch_file_attachment(kind='xml')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % att.id,
            'target': 'self',
        }

    def action_ehoadon_open_lookup(self):
        self.ensure_one()
        url = self.ehoadon_view_url
        if not url:
            raise UserError(_('Chưa có viewUrl tra cứu eHoaDon.'))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    @api.onchange('move_type')
    def _onchange_set_default_ehoadon_template(self):
        for move in self:
            if move.ehoadon_template_id:
                continue
            try:
                config = move._ehoadon_config()
                if config.default_template_id:
                    move.ehoadon_template_id = config.default_template_id
            except Exception:
                pass