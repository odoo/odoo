# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from . import models
<<<<<<< 82712e8a2a05304f568c477920bc721607a012d2:addons/l10n_account_withholding_tax_pos/__init__.py
||||||| fc8dd35cca57ee53f7fa041de5750f4b62fdeb93:addons/hr_contract/__init__.py
from . import report
from . import wizard
=======
from . import report
from . import wizard

_logger = logging.getLogger(__name__)


def uninstall_hook(env):
    try:
        env.ref('hr.menu_resource_calendar_view').parent_id = env.ref("hr.menu_config_employee")
        env.ref('hr.menu_view_hr_contract_type').parent_id = env.ref("hr.menu_config_recruitment")
        env.ref('hr.menu_view_hr_contract_type').active = False
        env.ref('hr.menu_view_hr_contract_type').sequence = 2
    except ValueError as e:
        _logger.warning(e)
>>>>>>> 4e2b0429f6935d42a8acf75e891a59203bceadd7:addons/hr_contract/__init__.py
