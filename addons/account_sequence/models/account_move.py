from odoo import models
from odoo.tools import index_exists


class AccountMove(models.Model):
    _inherit = 'account.move'

    _sql_constraints = [(
        'unique_name', "", "Another entry with the same name already exists.",
    )]

    def _auto_init(self):
        super()._auto_init()
        if not index_exists(self.env.cr, 'account_move_unique_name'):
            # Make all values of `name` different (naming them `name (1)`, `name (2)`...) so that we can add the following UNIQUE INDEX
            self.env.cr.execute("""
                WITH duplicated_sequence AS (
                    SELECT name, journal_id, state
                      FROM account_move
                     WHERE state = 'posted'
                       AND name != '/'
                  GROUP BY journal_id, name, state
                    HAVING COUNT(*) > 1
                ),
                to_update AS (
                    SELECT move.id,
                           move.name,
                           move.journal_id,
                           move.state,
                           move.date,
                           row_number() OVER(PARTITION BY move.name, move.journal_id ORDER BY move.name, move.journal_id, move.date) AS row_seq
                      FROM duplicated_sequence
                      JOIN account_move move ON move.name = duplicated_sequence.name
                                            AND move.journal_id = duplicated_sequence.journal_id
                                            AND move.state = duplicated_sequence.state
                ),
                new_vals AS (
                    SELECT id,
                           name || ' (' || (row_seq-1)::text || ')' AS name
                      FROM to_update
                     WHERE row_seq > 1
                )
                UPDATE account_move
                   SET name = new_vals.name
                  FROM new_vals
                 WHERE account_move.id = new_vals.id;
            """)
            self.env.cr.execute("""
                CREATE UNIQUE INDEX account_move_unique_name
                ON account_move(name, journal_id) WHERE (state = 'posted' AND name != '/');
            """)

    def _check_unique_sequence_number(self):
        return
