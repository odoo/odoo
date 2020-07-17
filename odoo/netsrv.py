# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import warnings
from odoo.logging_config import *

warnings.warn(
    "The odoo.netsrv module is a deprecated alias to the "
    "odoo.logging_config module. Please import the latter.",
    DeprecationWarning)
