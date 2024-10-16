# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import base


class ResCountryState(base.ResCountryState):

    l10n_in_tin = fields.Char('TIN Number', size=2, help="TIN number-first two digits")
