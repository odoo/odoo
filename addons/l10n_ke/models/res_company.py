# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models
from odoo.addons import account


class ResCompany(account.ResCompany):

    l10n_ke_oscu_is_active = fields.Boolean(
        string="Is OSCU active?",
        help="Whether this company is set up for OSCU flows.",
        compute='_compute_l10n_ke_oscu_is_active',
    )

    def _compute_l10n_ke_oscu_is_active(self):
        """ Overridden in enterprise when the OSCU module is used in the company"""
        self.l10n_ke_oscu_is_active = False
