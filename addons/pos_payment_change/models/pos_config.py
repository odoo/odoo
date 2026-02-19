# Copyright (C) 2020 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    _PAYMENT_CHANGE_POLICY_SELECTION = [
        ("refund", "Refund and Resale"),
        ("update", "Update Payments"),
    ]

    payment_change_policy = fields.Selection(
        selection=_PAYMENT_CHANGE_POLICY_SELECTION,
        default="refund",
        required=True,
        help="Payment Change Policy when users want"
        " to change the payment lines of a given PoS Order.\n"
        "* 'Refund and Resale': Odoo will refund the current"
        " Pos Order to cancel it, and create a new PoS Order"
        " with the correct payment lines.\n"
        "* 'Update Payments': Odoo will change payment lines.\n\n"
        "Note : In some countries the 'Update Payments' Option"
        " is not allowed by law, because orders history shouldn't"
        " not be altered.",
    )

    @api.constrains("payment_change_policy")
    def _check_payment_change_policy(self):
        # Check if certification module is installed
        # and if yes, if 'update payments' option is allowed
        module_states = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "l10n_fr_pos_cert")])
            .mapped("state")
        )
        if "installed" not in module_states:
            return
        for config in self.filtered(lambda x: x.payment_change_policy == "update"):
            if config.company_id._is_accounting_unalterable():
                raise ValidationError(
                    _(
                        "Unable to use the 'Update Payments' options"
                        " for companies that have unalterable accounting."
                    )
                )
