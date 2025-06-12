# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from . import models
from . import report
from . import wizard
<<<<<<< dd00b83f65abd3383e7c7f49f6d0729290403862

_logger = logging.getLogger(__name__)


def uninstall_hook(env):
    try:
        env.ref('hr.menu_resource_calendar_view').parent_id = env.ref("hr.menu_config_employee")
        env.ref('hr.menu_view_hr_contract_type').parent_id = env.ref("hr.menu_config_recruitment")
        env.ref('hr.menu_view_hr_contract_type').active = False
        env.ref('hr.menu_view_hr_contract_type').sequence = 2
    except ValueError as e:
        _logger.warning(e)
||||||| f889a6f2f9d12571743a7d89ce4dbfe1191e0cd4
=======

_logger = logging.getLogger(__name__)


def uninstall_hook(env):
    try:
        env.ref('hr.menu_resource_calendar_view').parent_id = env.ref("hr.menu_config_employee")
    except ValueError as e:
        _logger.warning(e)
>>>>>>> 29b53cf8f34225bc6722939c89f9d19eb502529f
