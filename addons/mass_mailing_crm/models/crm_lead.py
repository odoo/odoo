# -*- coding: utf-8 -*-
from odoo.addons import crm
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class CrmLead(models.Model, crm.CrmLead):
    _mailing_enabled = True
