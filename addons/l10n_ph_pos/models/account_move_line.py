# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # SC/PWD ID holder of an invoiced POS order line, as recorded on it (see
    # pos.order.line).
    l10n_ph_holder_partner_id = fields.Many2one(
        "res.partner",
        string="SC/PWD ID Holder Contact",
        index="btree_not_null",
    )
    l10n_ph_holder_name = fields.Char(string="SC/PWD ID Holder")
    l10n_ph_holder_id_number = fields.Char(string="SC/PWD ID Number")
    l10n_ph_holder_representative_name = fields.Char(string="SC/PWD Representative Name")
    l10n_ph_holder_representative_id = fields.Char(string="SC/PWD Representative ID")
