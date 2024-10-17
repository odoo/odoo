# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools

# compatibility imports
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc as jsonrpc
from odoo.addons.iap.tools.iap_tools import iap_authorize as authorize
from odoo.addons.iap.tools.iap_tools import iap_cancel as cancel
from odoo.addons.iap.tools.iap_tools import iap_capture as capture
from odoo.addons.iap.tools.iap_tools import iap_charge as charge
from odoo.addons.iap.tools.iap_tools import InsufficientCreditError

from .models.iap_account import IapAccount
from .models.iap_enrich_api import IapEnrichApi
from .models.iap_service import IapService
