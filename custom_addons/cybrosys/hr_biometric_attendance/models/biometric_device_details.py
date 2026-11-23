# -*- coding: utf-8 -*-
import logging

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    from zk import ZK
except ImportError:
    _logger.error("Please install pyzk library: pip3 install pyzk")
    ZK = None


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connecting biometric devices with Odoo."""
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(
        string='Device IP', required=True,
        help='The IP address of the Device')
    port_number = fields.Integer(
        string='Port Number', required=True,
        help='The Port Number of the Device')
    tz = fields.Selection(
        selection='_get_tz_list',
        string='Device Timezone',
        default='Asia/Riyadh',
        help='Timezone of the biometric device')
    last_download_time = fields.Datetime(
        string='Last Download Time',
        help='Last time attendance was downloaded')
    download_batch_size = fields.Integer(
        string='Download Batch Size', default=1000,
        help='Maximum number of records to download in a single batch')
    download_timeout = fields.Integer(
        string='Download Timeout', default=60,
        help='Timeout in seconds for download operation')
    auto_download = fields.Boolean(
        string='Auto Download', default=True,
        help='Enable automatic download via scheduled actions')
    year_filter = fields.Selection(
        selection=lambda self: [
            (str(year), str(year))
            for year in range(2018, fields.Datetime.now().year + 1)
        ],
        string='Year Filter',
        default=lambda self: str(fields.Datetime.now().year),
        help='Filter attendance data by year to reduce processing time')
    address_id = fields.Many2one(
        'res.partner', string='Working Address',
        help='Working address of the partner')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        help='Current Company')

    @api.model
    def _get_tz_list(self):
        return [(tz, tz) for tz in pytz.all_timezones]

    # -- Connection -----------------------------------------------------------

    def _connect_device(self, timeout=None):
        """Connect to biometric device, return connection object."""
        self.ensure_one()
        if not ZK:
            raise UserError(_("pyzk library not installed."))
        if not self.device_ip:
            raise UserError(
                _("Please configure IP address for device %s.") % self.name)
        if timeout is None:
            timeout = self.download_timeout or 60
        zk = ZK(self.device_ip, port=self.port_number, timeout=timeout,
                password=False, force_udp=False)
        try:
            conn = zk.connect()
            if not conn:
                raise UserError(
                    _("Failed to connect to device %s.") % self.name)
            return conn
        except UserError:
            raise
        except Exception as e:
            _logger.error("Connection to %s failed: %s", self.name, e)
            raise UserError(_("Connection failed: %s") % e)

    # -- Simple device actions ------------------------------------------------

    def action_test_connection(self):
        conn = self._connect_device(timeout=30)
        conn.disconnect()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Successfully Connected'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_restart_device(self):
        conn = self._connect_device(timeout=15)
        try:
            conn.restart()
        finally:
            conn.disconnect()

    def action_clear_attendance(self):
        for device in self:
            conn = device._connect_device(timeout=30)
            try:
                conn.enable_device()
                if not conn.get_attendance():
                    raise UserError(_('Attendance log is empty.'))
                conn.clear_attendance()
                self.env.cr.execute("DELETE FROM zk_machine_attendance")
            finally:
                conn.disconnect()

    # -- Biometric ID helpers -------------------------------------------------

    def get_all_biometric_ids(self):
        self.ensure_one()
        conn = self._connect_device()
        try:
            users = conn.get_users()
            return [str(user.user_id) for user in users] if users else []
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error fetching users from %s: %s", self.name, e)
            raise UserError(_("Failed to fetch users: %s") % e)
        finally:
            conn.disconnect()

    def get_unmapped_biometric_ids(self):
        self.ensure_one()
        all_ids = self.get_all_biometric_ids()
        if not all_ids:
            return []
        mapped_ids = self.env['biometric.attendance.sync']._get_valid_biometric_ids()
        return [bid for bid in all_ids if bid not in mapped_ids]

    def action_map_biometric_ids(self):
        self.ensure_one()
        unmapped = self.get_unmapped_biometric_ids()
        if not unmapped:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('All biometric IDs are already mapped.'),
                    'type': 'info',
                    'sticky': False,
                },
            }
        return {
            'name': _('Map Biometric IDs to Employees'),
            'type': 'ir.actions.act_window',
            'res_model': 'biometric.mapping.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_id': self.id},
        }

    # -- Download entry points (delegate to sync service) ---------------------

    def action_download_all_attendance(self):
        _logger.info("=== STARTING FULL ATTENDANCE DOWNLOAD ===")
        result = self.env['biometric.attendance.sync'].download_attendance(
            self, incremental=False, force=True)
        _logger.info("=== COMPLETED FULL ATTENDANCE DOWNLOAD ===")
        # Keep the button request lightweight: full historical absence generation
        # is intentionally decoupled and should be triggered separately.
        return result

    def action_download_incremental_attendance(self):
        _logger.info("=== STARTING INCREMENTAL ATTENDANCE DOWNLOAD ===")
        result = self.env['biometric.attendance.sync'].download_attendance(
            self, incremental=True, force=True)
        _logger.info("=== COMPLETED INCREMENTAL ATTENDANCE DOWNLOAD ===")
        return result

    def action_download_attendance(self, incremental=True, force=False):
        """Backward-compatible entry point."""
        return self.env['biometric.attendance.sync'].download_attendance(
            self, incremental=incremental, force=force)


    def action_generate_all_absences(self):
        """Manual trigger: full historical absence scan for all employees."""
        return self.env['biometric.attendance.sync'].action_generate_all_absences()

    # -- Cron -----------------------------------------------------------------

    @api.model
    def cron_download_incremental(self):
        return self.env['biometric.attendance.sync'].cron_download_incremental()
