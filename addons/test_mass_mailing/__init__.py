# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import data
from . import models

from .models.ir_qweb import IrQweb
from .models.mailing_models import (
    MailingPerformance, MailingPerformanceBlacklist,
    MailingTestBlacklist, MailingTestCustomer, MailingTestOptout, MailingTestPartner,
    MailingTestSimple, MailingTestUtm,
)
from .models.mailing_models_cornercase import MailingTestPartnerUnstored
from .models.mailing_models_utm import UtmTestSourceMixin, UtmTestSourceMixinOther
