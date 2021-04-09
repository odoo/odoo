##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    # we add this field so that when invoice is validated we can reconcile
    # move lines between check and invoice lines
    # igual se setea para todos los rechazos, tal vez mas adelante lo usamos
    # para otra cosa
    rejected_check_id = fields.Many2one(
        'account.check',
        'Rejected Check',
    )

    def button_draft(self):
        """
        Si al cancelar la factura la misma estaba vinculada a un rechazo
        intentamos romper la conciliacion del rechazo
        """
        for rec in self.filtered('rejected_check_id'):
            check = rec.rejected_check_id
            deferred_account = check.company_id._get_check_account('deferred')
            if (
                    check.state == 'rejected' and
                    check.type == 'issue_check' and
                    deferred_account.reconcile):
                deferred_account_line = rec.line_ids.filtered(
                    lambda x: x.account_id == deferred_account)
                deferred_account_line.remove_move_reconcile()
        return super().button_draft()

    def post(self):
        """
        Si al validar la factura, la misma tiene un cheque de rechazo asociado
        intentamos concilarlo
        """
        res = super().post()
        for rec in self.filtered('rejected_check_id'):
            check = rec.rejected_check_id
            if check.state == 'rejected' and check.type == 'issue_check':
                rec.rejected_check_id.handed_reconcile(rec)
        return res
