from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FidelityTransaction(models.Model):
    """
    `fidelity.transaction` is the model that will link `fidelity.program`
    with `fidelity.card`. Each time a program is used by a partner, a
    new transaction will be added with the points earned/used.

    This allows the partner to have a single fidelity card linked to
    multiple programs.

    This model also allows you to keep a history of program usage by
    customers/employees.
    """
    _name = 'fidelity.transaction'
    _description = "Fidelity Transaction"

    issued = fields.Float()
    used = fields.Float()
    state = fields.Selection([
            ('pending', "Pending"),
            ('done', "Done"),
            ('canceled', "Canceled"),
        ],
        default='pending',
        required=True,
    )

    # Where the transaction is coming from
    reward_id = fields.Many2one('fidelity.reward', index=True)
    rule_id = fields.Many2one('fidelity.rule', index=True)
    program_id = fields.Many2one('fidelity.program', required=True, index=True)
    balance_id = fields.Many2one('fidelity.balance', ondelete='cascade', required=True, index=True)

    # Linking to orders (sales, point_of_sale, etc.)
    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(model_field='order_model')

    @api.constrains('issued', 'used', 'reward_id', 'rule_id')
    def _check_issued_read_reward_rule(self):
        for transaction in self:
            if transaction.issued > 0 and not transaction.rule_id:
                raise ValidationError(_("Transactions issuing points must be linked to a rule."))
            if transaction.used > 0 and not transaction.reward_id:
                raise ValidationError(_("Transactions using points must be linked to a reward."))

    @api.constrains('issued', 'used')
    def _check_issued_used(self):
        for transaction in self:
            if transaction.issued < 0 or transaction.used < 0:
                raise ValidationError(_("Issued and Used points must be positive values."))
