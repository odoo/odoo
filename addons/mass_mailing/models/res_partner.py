# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model, base.ResPartner):
    _mailing_enabled = True
