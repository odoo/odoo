# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import utils
from . import wizard

import uuid


def init_initiating_microsoft_uuid(env):
    """ Sets the company name as the default value for the initiating
    party name on all existing companies once the module is installed. """
    config_parameter = env['ir.config_parameter'].sudo()
    microsoft_guid = config_parameter.get_param('microsoft_calendar.microsoft_guid', False)
    if not microsoft_guid:
        config_parameter.set_param('microsoft_calendar.microsoft_guid', str(uuid.uuid4()))
