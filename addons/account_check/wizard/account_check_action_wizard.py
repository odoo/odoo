##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AccountCheckActionWizard(models.TransientModel):
    _name = 'account.check.action.wizard'
    _description = 'Account Check Action Wizard'

    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )
    action_type = fields.Char(
        'Action type passed on the context',
        required=True,
    )

    def action_confirm(self):
        self.ensure_one()
        if self.action_type not in [
                'claim', 'bank_debit', 'reject', 'customer_return']:
            raise ValidationError(_(
                'Action %s not supported on checks') % self.action_type)
        checks = self.env['account.check'].browse(
            self._context.get('active_ids'))
        for check in checks:
            res = getattr(
                check.with_context(action_date=self.date), self.action_type)()
        if len(checks) == 1:
            return res
        else:
            return True
