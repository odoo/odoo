# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nVnSymbol(models.Model):
    _inherit = 'l10n_vn.symbol'

    usage = fields.Selection(
        selection_add=[('delivery_document', 'Delivery Document')],
        ondelete={'delivery_document': 'cascade'},
    )
