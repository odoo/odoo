# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ke_cu_proxy_address = fields.Char(
        default="http://localhost:8069",
        string='Control Unit Proxy Address',
        help='The address of the proxy server for the control unit.',
    )
