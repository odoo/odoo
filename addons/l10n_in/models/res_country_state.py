# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountryState(models.Model, base.ResCountryState):

    l10n_in_tin = fields.Char('TIN Number', size=2, help="TIN number-first two digits")
