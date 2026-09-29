import secrets
import string
from datetime import timedelta

from psycopg2.errors import UniqueViolation

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PAIRING_CODE_TTL_MINUTES = 15
MAX_CODE_GENERATION_RETRIES = 5
DEFAULT_MAX_PENDING_REQUESTS_PER_IP = 25
MAX_PENDING_REQUESTS_PER_IP_PARAM = 'pos_self_order.max_pending_pairing_requests_per_ip'


class PosSelfOrderKioskPairingRequest(models.Model):
    _name = 'pos_self_order.kiosk.pairing.request'
    _order = 'create_date desc'
    _description = 'Kiosk Device Pairing Request'

    config_id = fields.Many2one('pos.config', required=True, ondelete='cascade')
    device_id = fields.Many2one('pos_self_order.kiosk.device', required=False, ondelete='cascade')
    pairing_code = fields.Char(required=True)
    expiration_date = fields.Datetime(string="Expiration Date", required=True)
    ip_address = fields.Char('IP Address', readonly=True)
    user_agent = fields.Char('User Agent', readonly=True)
    approved = fields.Boolean(default=False)

    _pairing_code_unique = models.UniqueIndex("(pairing_code)")

    @api.model
    def _ip_reached_pending_limit(self, ip_address):
        if not ip_address:
            return False
        pending = self.search_count([
            ('ip_address', '=', ip_address),
            ('approved', '=', False),
            ('expiration_date', '>=', fields.Datetime.now()),
        ])
        return pending >= self._max_pending_requests_per_ip()

    @api.model
    def _create_request(self, config_id=None, ip_address=None, user_agent=None):
        now = fields.Datetime.now()

        if self._ip_reached_pending_limit(ip_address):
            raise UserError(_("Too many pending pairing requests from this IP. Please try again later."))

        for _attempt in range(MAX_CODE_GENERATION_RETRIES):
            try:
                with self.env.cr.savepoint():
                    return self.create({
                        'config_id': config_id.id,
                        'pairing_code': f"{config_id.id}{''.join(secrets.choice(string.digits) for _ in range(6))}",
                        'expiration_date': now + timedelta(minutes=PAIRING_CODE_TTL_MINUTES),
                        'ip_address': ip_address,
                        'user_agent': user_agent[:1024],
                    })
            except UniqueViolation:
                continue

        raise UserError(_("Unable to generate a unique pairing code. Please try again later."))

    def is_pending(self):
        self.ensure_one()
        return not self.approved and not self.is_expired()

    def is_expired(self):
        self.ensure_one()
        now = fields.Datetime.now()
        return self.expiration_date < now

    @api.model
    def _cron_cleanup_expired(self):
        expired = self.search([('expiration_date', '<', fields.Datetime.now())])
        expired.unlink()

    @api.model
    def _max_pending_requests_per_ip(self):
        return self.env["ir.config_parameter"].sudo().get_int(MAX_PENDING_REQUESTS_PER_IP_PARAM) or DEFAULT_MAX_PENDING_REQUESTS_PER_IP
