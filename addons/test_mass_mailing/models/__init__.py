# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .ir_qweb import IrQweb
from .mailing_models import (
    MailingPerformance, MailingPerformanceBlacklist, MailingTestBlacklist,
    MailingTestCustomer, MailingTestOptout, MailingTestPartner, MailingTestSimple, MailingTestUtm,
)
from .mailing_models_utm import UtmTestSourceMixin, UtmTestSourceMixinOther
from .mailing_models_cornercase import MailingTestPartnerUnstored
