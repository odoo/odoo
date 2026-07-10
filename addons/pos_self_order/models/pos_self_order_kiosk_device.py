import uuid
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import consteq
from odoo.tools._vendor.useragents import UserAgent
from odoo.tools.translate import _

PAIRING_GRACE_PERIOD = timedelta(minutes=5)
ACTIVITY_WRITE_THROTTLE = timedelta(minutes=5)
REFRESH_THRESHOLD = timedelta(days=1)


class PosSelfOrderKioskDevice(models.Model):
    _name = 'pos_self_order.kiosk.device'
    _order = 'last_activity desc'
    _description = 'Kiosk Device'
    _cookie_separator = '|'
    __user_agent_parser = UserAgent._parser

    config_id = fields.Many2one('pos.config', required=True, ondelete='cascade', index=True, readonly=True)
    ip_address = fields.Char('IP Address', readonly=True)
    user_agent = fields.Char('User Agent', readonly=True)
    platform = fields.Char('Platform', compute='_compute_kiosk_device_info', readonly=True)
    browser = fields.Char('Browser', compute='_compute_kiosk_device_info', readonly=True)
    browser_version = fields.Char('Browser Version', compute='_compute_kiosk_device_info', readonly=True)
    browser_language = fields.Char('Browser Language', compute='_compute_kiosk_device_info', readonly=True)
    first_activity = fields.Datetime('First Activity', required=True, readonly=True, default=fields.Datetime.now)
    last_activity = fields.Datetime('Last Activity', required=True, readonly=True, default=fields.Datetime.now)
    approved_by = fields.Many2one('res.users', required=True, readonly=True, string="Approved by")
    access_token = fields.Char(string="Access Token", default=lambda self: str(uuid.uuid4()), groups='base.group_system', required=True, readonly=True, copy=False)

    @api.model
    def _create_from_pairing(self, pairing_req):
        now = fields.Datetime.now()
        device = self._search_from_pairing_request(pairing_req)
        data = {
            'config_id': pairing_req.config_id.id,
            'approved_by': self.env.user.id,
            'ip_address': pairing_req.ip_address,
            'user_agent': pairing_req.user_agent,
        }
        if device:
            device.write(data)
        else:
            device = self.create(data)

        # Short grace period so the device can poll for approval status before the request expires.
        pairing_req.write({
            'device_id': device.id,
            'approved': True,
            'expiration_date': now + PAIRING_GRACE_PERIOD,
        })
        return device

    @api.model
    def _search_from_pairing_request(self, pairing_req):
        return self.env['pos_self_order.kiosk.device'].browse()

    @api.model
    def _client_info_from_request(self, request):
        return {
            'ip_address': request.httprequest.remote_addr,
            'user_agent': request.httprequest.user_agent.string[:1024],
        }

    def _create_from_request(self, request, config_id):
        device = self.create({
            'config_id': config_id,
            'approved_by': self.env.user.id,
            **self._client_info_from_request(request),
        })
        device._set_auth_cookie(request)
        return device

    def _set_auth_cookie(self, request):
        self.ensure_one()
        expiration_date = fields.Datetime.now() + timedelta(days=365)
        request.future_response.set_cookie(
            self._format_auth_cookie_name(self.config_id.id),
            self._format_auth_cookie(),
            httponly=True,
            secure=request.httprequest.is_secure,
            samesite='Lax',
            expires=expiration_date,
        )

    def _format_auth_cookie(self):
        self.ensure_one()
        return f"{self.id}{self._cookie_separator}{self.access_token}"

    @api.model
    def _format_auth_cookie_name(self, config_id):
        return f"psodid_{config_id}"

    @api.model
    def _get_kiosk_device_from_request(self, request, config_id=None):
        device = request.env.context.get('pos_self_device')
        if device and device.config_id.id == config_id:
            return device
        token = request.cookies.get(self._format_auth_cookie_name(config_id), "")
        device = self._get_kiosk_device_from_token(token)
        request.update_context(pos_self_device=device)
        return device

    @api.model
    def _get_or_create_kiosk_device_from_request(self, request, config_id=None):
        device = self._get_kiosk_device_from_request(request, config_id)
        if not device:
            device = self._create_from_request(request, config_id)
        return device

    def _touch_kiosk_device(self, request):
        self.ensure_one()
        now = fields.Datetime.now()
        last_activity = self.last_activity
        elapsed = (now - last_activity) if last_activity else None
        if elapsed is None or elapsed >= ACTIVITY_WRITE_THROTTLE:
            self.sudo().write({'last_activity': now, **self._client_info_from_request(request)})
        if elapsed is None or elapsed >= REFRESH_THRESHOLD:
            self.sudo()._set_auth_cookie(request)

    @api.model
    def _get_and_touch_kiosk_device(self, request, config_id=None):
        device = self._get_kiosk_device_from_request(request, config_id)
        if device:
            device._touch_kiosk_device(request)
        return device

    def _get_kiosk_device_from_token(self, token=""):
        empty_device = self.env['pos_self_order.kiosk.device']
        parts = token.split(self._cookie_separator)
        if len(parts) != 2:
            return empty_device
        device_id, device_access_token = parts
        device = self.sudo().browse(int(device_id)).exists()
        if not device or not device.access_token or not consteq(device.access_token, device_access_token):
            return empty_device
        return device.sudo(False)

    def _compute_kiosk_device_info(self):
        for device in self:
            platform, browser, browser_version, browser_language = self.__user_agent_parser(device.user_agent or '')
            device.platform = platform or _('Unknown')
            device.browser = browser or _('Unknown')
            device.browser_version = browser_version or _('Unknown')
            device.browser_language = browser_language or _('Unknown')
