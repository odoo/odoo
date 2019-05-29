# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
# from odoo.exceptions import UserError
from odoo.osv import expression


class AccountMove(models.Model):

    _inherit = "account.move"

    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        'Document Type',
        copy=False,
        auto_join=True,
        states={'posted': [('readonly', True)]},
        index=True,
    )
