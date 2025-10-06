# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.account.models.account_journal import JOURNAL_TYPE


class AccountMoveSetJournalWizard(models.TransientModel):
    _name = 'account.move.set.journal.wizard'
    _description = "Set Journal for Account Moves"

    move_ids = fields.Many2many('account.move')
    company_id = fields.Many2one('res.company', readonly=True)
    journal_type = fields.Selection(selection=JOURNAL_TYPE)
    journal_id = fields.Many2one(
        'account.journal',
        string="Journal",
        required=True,
        check_company=True,
        domain="[('type', '=', journal_type)]",
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') != 'account.move' or not active_ids:
            raise UserError(self.env._("This action can only be performed on selected account moves."))

        moves = self.env['account.move'].browse(active_ids)
        if moves.filtered(lambda m: m.state != 'draft'):
            raise UserError(self.env._("The selected entries must be in a draft state to set a journal."))
        if len(company := moves.mapped('company_id')) > 1:
            raise UserError(self.env._("The selected entries must belong to the same company to set a journal."))
        if len(journal_types := moves.mapped('journal_id.type')) > 1:
            raise UserError(self.env._("The selected entries must have the same journal type to set a journal."))
        company_id = company.id if company else self.env.company.id
        journal_type = journal_types[0] if journal_types else False
        journals_exist = self.env['account.journal'].search_count([
            ('company_id', '=', company_id),
            ('type', '=', journal_type),
        ])
        if journals_exist < 2:
            raise UserError(self.env._("Only one %s journal exists and it is already set.", journal_type))

        res.update({
            'move_ids': [Command.set(moves.ids)],
            'company_id': company_id,
            'journal_type': journal_type,
        })
        return res

    def action_set_journal(self):
        self.ensure_one()
        self.move_ids.write({'journal_id': self.journal_id.id})
        return {'type': 'ir.actions.act_window_close'}
