# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import lib
from . import tools
from . import models
from . import wizard

from .models.mail_thread_phone import MailThreadPhone
from .models.models import Base
from .models.phone_blacklist import PhoneBlacklist
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .wizard.phone_blacklist_remove import PhoneBlacklistRemove
