# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from . import models
from . import report
from . import wizard

_logger = logging.getLogger(__name__)


def uninstall_hook(env):
    try:
        env.ref('hr.menu_resource_calendar_view').parent_id = env.ref("hr.menu_config_employee")
    except ValueError as e:
        _logger.warning(e)
