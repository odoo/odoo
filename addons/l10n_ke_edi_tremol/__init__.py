# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
from . import models
from . import wizard

from .models.account_move import AccountMove
from .models.account_move_send import AccountMoveSend
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .wizard.account_move_send_wizard import AccountMoveSendWizard
