# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import mail, contacts


class ResPartner(contacts.ResPartner, mail.ResPartner):
    _mailing_enabled = True
