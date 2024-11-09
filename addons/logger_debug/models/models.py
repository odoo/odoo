
import logging
from odoo import models, fields, api
from odoo.addons.logger_debug.tools.log_filter_debug import get_log_filter_debug_db

_logger = logging.getLogger(__name__)


class LoggerDebug(models.Model):
    _name = 'logger_debug.logger_debug'
    _description = 'Switch log level to DEBUG to any odoo module'

    @staticmethod
    def _debug_module(module_name: str):
        """Debug a module by setting the log level to DEBUG."""
        get_log_filter_debug_db().add_logger(module_name)

    def _register_hook(self):
        super()._register_hook()
        #TODO: add real code here (read logger name the table, etc.)
        self._debug_module('odoo.addons.logger_debug.controllers.controllers')

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
