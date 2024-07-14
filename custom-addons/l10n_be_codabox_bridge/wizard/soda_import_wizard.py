from markupsafe import Markup
from odoo import Command, _, fields, models


class SodaImportWizard(models.TransientModel):
    _inherit = 'soda.import.wizard'
    soda_code_to_name_mapping = fields.Json(required=False)

    def _action_save_and_import(self):
        soda_account_mapping = {}
        for mapping in self.soda_account_mapping_ids:
            soda_account_mapping[mapping.code] = {
                'account_id': mapping.account_id.id,
                'name': mapping.name,
            }

        if self.env.context.get('soda_mapping_save_only', False):
            return False

        non_mapped_soda_accounts = set()
        moves = self.env['account.move']
        for ref, soda_file in self.soda_files.items():
            # We create a move for every SODA file containing the entries according to the mapping
            move_vals = {
                'move_type': 'entry',
                'journal_id': self.journal_id.id,
                'ref': ref,
                'line_ids': [],
                'date': soda_file['date']
            }
            for entry in soda_file['entries']:
                account_id = soda_account_mapping[entry['code']]['account_id']
                if not account_id:
                    account_id = self.journal_id.company_id.account_journal_suspense_account_id.id
                    non_mapped_soda_accounts.add((entry['code'], entry['name']))
                move_vals['line_ids'].append(
                    Command.create({
                        'name': entry['name'] or soda_account_mapping[entry['code']]['name'],
                        'account_id': account_id,
                        'debit': entry['debit'],
                        'credit': entry['credit'],
                    })
                )
            move = self.env['account.move'].create(move_vals)
            attachment = self.env['ir.attachment'].browse(soda_file['attachment_id'])
            move.message_post(attachment_ids=[attachment.id])
            if non_mapped_soda_accounts:
                move.message_post(
                    body=Markup("{first}<ul>{accounts}</ul>{second}<br/>{link}").format(
                        first=_("The following accounts were found in the SODA file but have no mapping:"),
                        accounts=Markup().join(
                            Markup("<li>%s (%s)</li>") % (code, name)
                            for code, name in non_mapped_soda_accounts
                        ),
                        second=_("They have been imported in the Suspense Account (499000) for now."),
                        link=_("For future imports, you can map them correctly in %s",
                            Markup("<a href=#action=l10n_be_codabox_bridge.action_open_accounting_settings&model=res.config.settings>%s</a>")
                            % _("Configuration > Settings > Accounting > CodaBox"),
                       ),
                    )
                )
            attachment.write({'res_model': 'account.move', 'res_id': move.id})
            moves += move
        return moves
