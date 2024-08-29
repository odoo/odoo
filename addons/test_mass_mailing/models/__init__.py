# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .ir_qweb import IrQweb
from .mailing_models import MailingTestPartner, MailingPerformance, MailingTestSimple, MailingTestUtm, MailingTestCustomer, MailingPerformanceBlacklist, MailingTestOptout, MailingTestBlacklist
from .mailing_models_utm import UtmTestSourceMixinOther, UtmTestSourceMixin
from .mailing_models_cornercase import MailingTestPartnerUnstored
