# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_vn_type = fields.Char(default='01GTKT')
    l10n_vn_template_code = fields.Char(default='01GTKT0/002')
    l10n_vn_series = fields.Char(default='KM/20E')
    l10n_vn_authority = fields.Char(default='')
    l10n_vn_base_url = fields.Char(default='https://api-sinvoice.viettel.vn:443')
