# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class AccountEdiFormat(models.Model):

    _inherit = 'account.edi.format'

    def _check_move_configuration(self, move):
        # EXTENDS account.edi.format
        errors = super()._check_move_configuration(move)
        if move.l10n_ec_sri_payment_id and move.l10n_ec_sri_payment_id.code == 'mpm' and move.move_type == 'out_invoice':
            for payment in move.pos_order_ids.payment_ids:
                if not payment.payment_method_id.l10n_ec_sri_payment_id:
                    errors.append(_("You must set the Payment Method SRI on all the payment methods for document %s", move.display_name))
                    break
        return errors
