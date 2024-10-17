# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.privacy_log import PrivacyLog
from .models.res_partner import ResPartner
from .wizard.privacy_lookup_wizard import PrivacyLookupWizard, PrivacyLookupWizardLine
