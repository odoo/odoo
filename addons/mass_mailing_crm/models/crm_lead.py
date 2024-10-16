# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import crm


class CrmLead(crm.CrmLead):
    _mailing_enabled = True
