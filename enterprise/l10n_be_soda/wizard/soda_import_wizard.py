from markupsafe import Markup
from odoo import Command, _, api, fields, models


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
    soda_code_to_name_mapping = fields.Json(required=False)
    company_id = fields.Many2one('res.company', required=True)
    journal_id = fields.Many2one('account.journal')
    soda_account_mapping_ids = fields.Many2many('soda.account.mapping', compute='_compute_soda_account_mapping_ids', readonly=False)

    @api.depends('soda_code_to_name_mapping', 'company_id')
    def _compute_soda_account_mapping_ids(self):
        for wizard in self:
            soda_account_mappings = self.env['soda.account.mapping'].find_or_create_mapping_entries(
                wizard.soda_code_to_name_mapping,
                self.company_id
            )
            wizard.soda_account_mapping_ids = [Command.set(soda_account_mappings.ids)]

    def _action_save_and_import(self, existing_move=None):
        # We find all mapping lines where there's no account set
        soda_account_mapping = {}
        for mapping in self.soda_account_mapping_ids:
            soda_account_mapping[mapping.code] = {'account_id': mapping.account_id.id, 'name': mapping.name}

        if self.env.context.get('soda_mapping_save_only', False):
            return False

        suspense_account = self.journal_id.company_id.account_journal_suspense_account_id
        non_mapped_soda_accounts = set()
        moves = self.env['account.move']
        line_ids = []
        for ref, soda_file in self.soda_files.items():
            # Every SODA file is linked to a move containing the entries according to the mapping
            for entry in soda_file['entries']:
                account_id = soda_account_mapping[entry['code']]['account_id']
                if not account_id:
                    account_id = suspense_account.id
                    non_mapped_soda_accounts.add((entry['code'], entry['name']))
                line_ids.append(
                    Command.create({
                        'name': entry['name'] or soda_account_mapping[entry['code']]['name'],
                        'account_id': account_id,
                        'debit': entry['debit'],
                        'credit': entry['credit'],
                    })
                )
            if not existing_move:
                move_vals = {
                    'move_type': 'entry',
                    'journal_id': self.journal_id.id,
                }
                move = self.env['account.move'].create(move_vals)
                attachment = self.env['ir.attachment'].browse(soda_file['attachment_id'])
                move.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])
                attachment.write({'res_model': 'account.move', 'res_id': move.id})
            else:
                move = existing_move
                # Avoid updating the same move multiple times. Should not happen as existing_move is set when
                # importing from email alias where _action_save_and_import method is called once per soda file.
                existing_move = None

            move.with_context(tracking_disable=True).write({
                'ref': ref,
                'date': soda_file['date'],
                'line_ids': line_ids,
            })
            if non_mapped_soda_accounts:
                move.message_post(
                    body=Markup("{first}<ul>{accounts}</ul>{second}<br/>{link}").format(
                        first=_("The following accounts were found in the SODA file but have no mapping:"),
                        accounts=Markup().join(Markup("<li>%s (%s)</li>") % (code, name) for code, name in non_mapped_soda_accounts),
                        second=_("They have been imported in the Suspense Account (499000) for now."),
                        link=_(
                            "For future imports, you can map them correctly in %(left)sConfiguration > Settings > Accounting > SODA%(right)s",
                            left=Markup("<a href='#action=l10n_be_soda.action_open_accounting_settings&model=res.config.settings'>"),
                            right=Markup("</a>"),
                        ),
                    )
                )
            if errors := self.env.context.get('errors', False):
                for error in errors:
                    move.message_post(body=error)
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
        if not moves:
            return False
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
