# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import base


class ResCountry(base.ResCountry):

    l10n_cl_customs_code = fields.Char('Customs Code')
    l10n_cl_customs_name = fields.Char('Customs Name')
    l10n_cl_customs_abbreviation = fields.Char('Customs Abbreviation')
