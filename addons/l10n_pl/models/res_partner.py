# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account, base_vat


class ResPartner(base_vat.ResPartner, account.ResPartner):
    """Inherited to add the information needed for the JPK"""

    l10n_pl_links_with_customer = fields.Boolean(
        string='Links With Company',
        help='TP: Existing connection or influence between the customer and the supplier'
    )
