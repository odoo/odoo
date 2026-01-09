# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    l10n_in_gsp = fields.Selection(selection=[
        ('bvm_it_consulting', 'BVM IT Consulting'),
        ('tera_software', 'Tera Software (Deprecated)'),
    ], string="GSP", default='tera_software', required=True,
        help="Select the GST Suvidha Provider (GSP) you want to use to file your GST returns electronically.",
        config_parameter='l10n_in.gst_gsp_provider',
    )
