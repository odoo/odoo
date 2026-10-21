# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EhoadonTemplate(models.Model):
    _name = 'ehoadon.template'
    _description = 'eHoaDon Invoice Template'

    name = fields.Char(string='Name', required=True)
    serial = fields.Char(
        string='Ký hiệu / Serial hóa đơn',
        required=True,
        help=(
            'Mapped to AddEInvoice.serial. Must be a ký hiệu the API user '
            'is allowed to issue on this MST host (portal eHoaDon / mẫu đã đăng ký).'
        ),
    )
    is_cash_register = fields.Boolean(
        string='Máy tính tiền (CashRegister API)',
        default=False,
        help='If set, use Api/CashRegister/* instead of EInvoiceOnline/*.',
    )
    available_serials_json = fields.Text(
        string='Available serials (last sync)',
        readonly=True,
        copy=False,
    )
    vat_rate_mode = fields.Selection(
        selection=[
            ('per_item', 'Đa thuế suất (VatPerItem)'),
            ('per_invoice', 'Một thuế suất (VatPerInvoice)'),
        ],
        string='Loại mẫu thuế suất',
        compute='_compute_vat_rate_mode',
        store=True,
        readonly=False,
        help='From GetAvailiableSerial Group of the serial. '
             'Multi-rate: header vatRate = 0. Single-rate: header vatRate = default_vat_rate.',
    )
    default_vat_rate = fields.Float(
        string='Thuế suất mặc định (vatRate)',
        default=10.0,
        help='Header vatRate sent for single-rate (VatPerInvoice) serials.',
    )
    invoice_mtt = fields.Boolean(
        string='Hóa đơn bán hàng đã gồm VAT',
        default=False,
        help='If set, line amounts are treated as VAT-inclusive (taxAmount=0 path).',
    )
    payment_method = fields.Selection(
        selection=[
            ('1', 'Cash'),
            ('2', 'Transfer'),
            ('3', 'Cash or Transfer (TM/CK)'),
            ('4', 'Credit'),
            ('8', 'Other'),
        ],
        string='Phương thức thanh toán',
        default='3',
        required=True,
    )
    email = fields.Char(string='API Email')
    password = fields.Char(string='API Password')
    tenant_id = fields.Char(string='Tenant ID')
    tax_number = fields.Char(
        string='Mã số thuế cho Endpoint',
        help='MST host: https://{tax_number}.ehoadon.net',
    )
    endpoint_host = fields.Char(string='API host override')
    access_token = fields.Char(string='Access Token (cache)', readonly=True)
    access_token_expiry = fields.Datetime(string='Access Token Expiry', readonly=True)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Notes')
    config_id = fields.Many2one(
        'ehoadon.config',
        string='Cấu hình',
        default=lambda self: self.env['ehoadon.config'].get_ehoadon_config().id,
        ondelete='cascade',
        index=True,
        required=True,
    )
    is_default = fields.Boolean(
        string='Mặc định',
        compute='_compute_is_default',
        inverse='_inverse_is_default',
        store=False,
    )

    _sql_constraints = [
        (
            'ehoadon_template_serial_unique',
            'unique(serial)',
            'Ký hiệu (serial) phải là duy nhất.',
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        config = self.env['ehoadon.config'].get_ehoadon_config()
        for vals in vals_list:
            vals.setdefault('email', config.email)
            vals.setdefault('password', config.password)
            vals.setdefault('tenant_id', config.tenant_id)
            vals.setdefault('tax_number', config.tax_number)
        return super().create(vals_list)

    @api.depends('serial', 'available_serials_json')
    def _compute_vat_rate_mode(self):
        group_to_mode = {'VatPerItem': 'per_item', 'VatPerInvoice': 'per_invoice'}
        for rec in self:
            mode = False
            serial = (rec.serial or '').strip()
            try:
                rows = json.loads(rec.available_serials_json or '[]')
            except ValueError:
                rows = []
            for row in rows if isinstance(rows, list) else []:
                value = row.get('Value') or row.get('value') or row.get('Text') or ''
                if serial and value.strip() == serial:
                    mode = group_to_mode.get(row.get('Group') or row.get('group'))
                    break
            rec.vat_rate_mode = mode or rec.vat_rate_mode or 'per_item'

    def _compute_is_default(self):
        config = self.env['ehoadon.config'].get_ehoadon_config()
        default_id = config.default_template_id.id if config.default_template_id else False
        for rec in self:
            rec.is_default = bool(default_id and rec.id == default_id)

    def _inverse_is_default(self):
        config = self.env['ehoadon.config'].get_ehoadon_config()
        for rec in self:
            if rec.is_default:
                config.default_template_id = rec.id
            elif config.default_template_id.id == rec.id:
                config.default_template_id = False

    def action_get_token(self):
        """POST /Api/Token/Create using Email/Password/TenantId + tax_number as host."""
        self.ensure_one()
        config = self.env['ehoadon.config'].get_ehoadon_config()
        token, error = config.get_access_token(template=self, force_refresh=True)
        if error:
            raise UserError(error)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('eHoaDon'),
                'message': _('Đã lấy token thành công.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_sync_available_serials(self):
        """GET GetAvailiableSerial — fill available_serials_json; optionally match serial."""
        self.ensure_one()
        config = self.env['ehoadon.config'].get_ehoadon_config()
        path = config.ehoadon_path('serials', template=self)
        resp, error = config.api_call('GET', path, template=self)
        if error:
            raise UserError(error)
        data = resp.get('data') or []
        if not isinstance(data, list):
            raise UserError(_('GetAvailiableSerial không trả list.'))
        self.available_serials_json = json.dumps(data, ensure_ascii=False, indent=2)
        # If current serial matches a row, sync IsCashRegister.
        matched = None
        for row in data:
            value = row.get('Value') or row.get('value') or row.get('Text') or row.get('text')
            if value and self.serial and value.strip() == self.serial.strip():
                matched = row
                break
        vals = {}
        if matched:
            if 'IsCashRegister' in matched or 'isCashRegister' in matched:
                vals['is_cash_register'] = bool(
                    matched.get('IsCashRegister', matched.get('isCashRegister'))
                )
        if vals:
            self.write(vals)
        values = [
            (r.get('Value') or r.get('value') or r.get('Text') or '')
            for r in data
        ]
        msg = _('Đã tải %s ký hiệu: %s') % (
            len(data),
            ', '.join(v for v in values if v)[:300],
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('eHoaDon'),
                'message': msg,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }
