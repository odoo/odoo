# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models
from odoo.exceptions import UserError


class AccountMoveSetJournalWizard(models.TransientModel):
    _name = 'account.move.set.journal.wizard'
    _description = "Set Journal for Account Moves"

    move_ids = fields.Many2many('account.move')
    company_id = fields.Many2one('res.company', readonly=True)
    journal_id = fields.Many2one(
        'account.journal',
        string="Journal",
        required=True,
        check_company=True,
        domain="[('type', '=', 'purchase')]",
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('active_model') != 'account.move':
            raise UserError(self.env._("This action can only be performed from vendor bills or credit notes."))
        active_ids = self.env.context.get('active_ids', [])
        moves = self.env['account.move'].browse(active_ids)
        if moves.filtered(lambda m: m.state != 'draft' or m.move_type not in ('in_invoice', 'in_refund')):
            raise UserError(self.env._("The selected entries must be draft vendor bills or credit notes to set journal."))
        if len(company := moves.mapped('company_id')) > 1:
            raise UserError(self.env._("The selected entries must belong to the same company to set journal."))
        company_id = company.id if company else self.env.company.id
        journals_exist = self.env['account.journal'].search_count([
            ('company_id', '=', company_id),
            ('type', '=', 'purchase')
        ])
        if journals_exist < 2:
            raise UserError(self.env._("At least 2 purchase journals must exist to set journal for entries."))

        res.update({
            'move_ids': [Command.set(moves.ids)],
            'company_id': company_id,
        })
        return res

    def action_set_journal(self):
        self.ensure_one()
        self.move_ids.write({'journal_id': self.journal_id.id})
        return {'type': 'ir.actions.act_window_close'}
