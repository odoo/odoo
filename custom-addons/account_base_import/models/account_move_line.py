# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = ["account.move.line"]

    @api.model
    def load(self, fields, data):
        """ Overriden to handle Journal Items import.
        Data and fields are split into two:
            - move_id, journal_id, date are passed to 'account.move' load()
            - the rest of fields is passed to 'account.move.line' load()
        This is because the account.move cannot be created with one aml, as it needs to be balanced.
        Journals are created first to override the sequence regex. This is because the move name
        comes from the external software during import and might conflict with the journal sequence
        format and prevent correct import.
        Create the moves first, then the amls."""
        def _sequence_override(journals, regex=False):
            for journal in journals:
                journal.sequence_override_regex = regex

        if "import_file" in self.env.context:
            account_move_data = []
            processed_move_ids = set() # avoid creating several moves with the same name
            journal_data = set()
            required_fields = ("journal_id", "move_id", "date")
            if not all(field in fields for field in required_fields):
                missing_fields = ", ".join(field for field in required_fields if field not in fields)
                raise UserError(_("The import file is missing the following required columns: %s", missing_fields))
            journal_index = fields.index("journal_id")
            move_index = fields.index("move_id")
            date_index = fields.index("date")

            for row in data:
                journal_id = row[journal_index]
                move_id = row[move_index]
                date = row[date_index]
                if move_id in processed_move_ids:
                    continue
                account_move_data.append([journal_id, move_id, date])
                processed_move_ids.add(move_id)
                journal_data.add(journal_id)

            # journals may or may not exist - load_records will create them if they don't
            # but we need to pass ids to prevent creation if they already exist
            journal_codes_ids = {}
            journal_codes = self.env["account.journal"].search_read(
                domain=self.env['account.journal']._check_company_domain(self.env.company),
                fields=["code"]
            )
            for journal in journal_codes:
                journal_codes_ids[journal["code"]] = journal["id"]

            journal_ids = self.env["account.journal"]._load_records([{"values": {"name": journal_name, "id": journal_codes_ids.get(journal_name[:5], False)}} for journal_name in journal_data])
            _sequence_override(journal_ids, r"^(?P<prefix1>.*?)(?P<seq>\d{0,9})(?P<suffix>\D*?)$")
            self.env["account.move"].load(["journal_id", "name", "date"], account_move_data)

            # override back to the default after all moves are created
            _sequence_override(journal_ids)

            if 'matching_number' in fields:
                matching_index = fields.index('matching_number')
                for row in data:
                    row[matching_index] = row[matching_index] and f"I{row[matching_index]}"

        return super().load(fields, data)
