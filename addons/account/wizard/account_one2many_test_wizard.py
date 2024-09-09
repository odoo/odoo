from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError


class AccountOne2manyTestWizard(models.TransientModel):
    _name = 'account.one2many.test.wizard'
    _description = "Account One2many test wizard"

    account_ids = fields.Many2many('account.account')
    some_field = fields.Char('Some Field')
    wizard_line_ids = fields.One2many(
        comodel_name='account.one2many.test.wizard.line',
        inverse_name='wizard_id',
        compute='_compute_wizard_line_ids',
        store=True,
        readonly=False,
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not set(fields) & {'account_ids', 'wizard_line_ids'}:
            return res

        if self.env.context.get('active_model') != 'account.account' or not self.env.context.get('active_ids'):
            raise UserError(_("This can only be used on accounts."))

        res['account_ids'] = [Command.set(self.env.context.get('active_ids'))]
        return res

    @api.depends('some_field', 'account_ids')
    def _compute_wizard_line_ids(self):
        """ Determine which accounts to merge together. """
        for wizard in self:
            wizard_lines_vals_list = [
                {
                    'sequence': sequence,
                    'account_id': account.id,
                }
                for sequence, account in enumerate(wizard.account_ids)
            ]

            wizard.wizard_line_ids = [Command.unlink(wizard_line.id) for wizard_line in wizard.wizard_line_ids] + \
                                     [Command.create(vals) for vals in wizard_lines_vals_list]


class AccountOne2manyTestWizardLine(models.TransientModel):
    _name = 'account.one2many.test.wizard.line'
    _description = "Account One2many test wizard line"
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        comodel_name='account.one2many.test.wizard',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer()
    account_id = fields.Many2one(comodel_name='account.account')
