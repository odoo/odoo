from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class SodaImportWizard(models.TransientModel):
    _name = 'soda.import.wizard'
    _description = 'Import a SODA file and map accounts'

    # A dict mapping the SODA reference to a dict with a list of `entries` and an `attachment_id`
    # {
    #     'soda_reference_1': {
    #         'entries': [
    #             {
    #                 'code': '1200',
    #                 'name': 'Line Description',
    #                 'debit': '150.0',
    #                 'credit': '0.0',
    #             },
    #             ...
    #         ],
    #         'attachment_id': 'attachment_id_1',
    #     },
    #     ...
    # }
    soda_files = fields.Json()
    # A dict mapping the SODA account code to its description
    soda_code_to_name_mapping = fields.Json(required=True)
    company_id = fields.Many2one('res.company', required=True)
    journal_id = fields.Many2one('account.journal', required=True)
    soda_account_mapping_ids = fields.Many2many('soda.account.mapping', compute='_compute_soda_account_mapping_ids', readonly=False)

    @api.depends('soda_code_to_name_mapping', 'company_id')
    def _compute_soda_account_mapping_ids(self):
        for wizard in self:
            soda_account_mappings = self.env['soda.account.mapping'].find_or_create_mapping_entries(
                wizard.soda_code_to_name_mapping,
                self.company_id
            )
            wizard.soda_account_mapping_ids = [Command.set(soda_account_mappings.ids)]

    def _action_save_and_import(self):
        # We find all mapping lines where there's no account set
        empty_mappings = self.soda_account_mapping_ids.filtered(lambda m: not m.account_id)
        if empty_mappings:
            new_account_codes = empty_mappings.mapped('code')
            existing_accounts = self.env['account.account'].search(
                [('code', 'in', new_account_codes), ('company_id', '=', self.company_id.id)]
            )
            # If there's no account set, but there exists one in the database, we raise an error and the user should
            # select the right account in the wizard.
            if len(existing_accounts) == 1:
                raise UserError(_(
                    'Could not create the account %(account_code)s. An account with this number already exists.',
                    account_code=existing_accounts.code
                ))
            elif len(existing_accounts) > 1:
                raise UserError(_(
                    'Could not create the following accounts: %(account_codes)s. Accounts with these numbers already exist.',
                    account_codes=', '.join(existing_accounts.mapped('code'))
                ))

            # We create the new accounts for the empty SODA mappings
            new_accounts = self.env['account.account'].create([{
                'code': code,
                'name': self.soda_code_to_name_mapping[code],
                'company_id': self.company_id.id,
            } for code in new_account_codes])

            # We assign the new accounts to the right SODA mappings
            for mapping in empty_mappings:
                mapping.account_id = new_accounts.search([('code', '=', mapping.code)])

        soda_account_mapping = {}
        for mapping in self.soda_account_mapping_ids:
            soda_account_mapping[mapping.code] = {'account_id': mapping.account_id.id, 'name': mapping.name}

        moves = self.env['account.move']
        for ref, soda_file in self.soda_files.items():
            # We create a move for every SODA file containing the entries according to the mapping
            move_vals = {
                'move_type': 'entry',
                'journal_id': self.journal_id.id,
                'ref': ref,
                'date': soda_file['date'],
                'line_ids': [Command.create({
                    'name': entry['name'] or soda_account_mapping[entry['code']]['name'],
                    'account_id': soda_account_mapping[entry['code']]['account_id'],
                    'debit': entry['debit'],
                    'credit': entry['credit'],
                }) for entry in soda_file['entries']],
            }
            move = self.env['account.move'].create(move_vals)
            attachment = self.env['ir.attachment'].browse(soda_file['attachment_id'])
            move.message_post(attachment_ids=[attachment.id])
            attachment.write({'res_model': 'account.move', 'res_id': move.id})
            moves += move
        return moves

    def action_save_and_import(self):
        moves = self._action_save_and_import()
        if not moves:       # When modifying (from the Settings) the mapping without importing a file,
            return False    # we don't want to redirect to the form/list view
        action_vals = {
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'context': self._context,
        }
        if len(moves) == 1:
            action_vals.update({
                'domain': [('id', '=', moves[0].ids)],
                'views': [[False, "form"]],
                'view_mode': 'form',
                'res_id': moves[0].id,
            })
        else:
            action_vals.update({
                'domain': [('id', 'in', moves.ids)],
                'views': [[False, "list"], [False, "kanban"], [False, "form"]],
                'view_mode': 'list, kanban, form',
            })
        # Redirect to the newly created move(s)
        return action_vals
