# -*- coding: utf-8 -*-

import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)

try:
    import debugpy
except ImportError:
    _logger.debug("Could not import debugpy")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    debugpy_wait_for_client = fields.Boolean(string="Debugpy Wait for Client", config_parameter='debugpy.wait_for_client')
    debugpy_host = fields.Char(string="Debugpy Host", default="0.0.0.0", config_parameter='debugpy.host')
    debugpy_port = fields.Integer(string="Debugpy Port", default=5678, config_parameter='debugpy.port')
    debugpy_logging = fields.Boolean(string="Debugpy Logging", config_parameter='debugpy.logging')
    debugpy_log_to = fields.Char(string="Debugpy Log To", default='/var/log/odoo/debugpy', config_parameter='debugpy.log_to')
    debugpy_is_installed = fields.Boolean(string="Debugpy Is Installed", compute='_compute_debugpy_is_installed', store=False, readonly=True)

    @api.depends('debugpy_host', 'debugpy_port', 'debugpy_wait_for_client', 'debugpy_logging', 'debugpy_log_to')
    def _compute_debugpy_is_installed(self):
        try:
            debugpy
        except NameError:
            result = False
        else:
            result = True

        for record in self:
            record.debugpy_is_installed = result
        return

    debugpy_is_client_connected = fields.Boolean(string="Debugpy Is Client Connected", compute='_compute_debugpy_is_client_connected', store=False, readonly=True)

    @api.depends('debugpy_host', 'debugpy_port', 'debugpy_wait_for_client', 'debugpy_logging', 'debugpy_log_to')
    def _compute_debugpy_is_client_connected(self):
        for record in self:
            if record.debugpy_is_installed:
                record.debugpy_is_client_connected = debugpy.is_client_connected()
            else:
                record.debugpy_is_client_connected = False
        return

    def action_debugpy_listen(self):
        self.ensure_one()
        if self.debugpy_is_installed:
            if self.debugpy_logging:
                debugpy.log_to(self.debugpy_log_to)

            debugpy.listen((self.debugpy_host, self.debugpy_port))

            if self.debugpy_wait_for_client:
                debugpy.wait_for_client()
        return

    def action_debugpy_test(self):
        self.ensure_one()

        if self.debugpy_is_installed:
            debugpy.breakpoint()
        return
