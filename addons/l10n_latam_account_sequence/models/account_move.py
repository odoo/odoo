from odoo import models
from odoo.tools.sql import index_exists, drop_index


class AccountMove(models.Model):
    _inherit = 'account.move'

    _sql_constraints = [(
        'unique_name', "", "Another entry with the same name already exists.",
    ), (
        'unique_name_latam', "", "Another entry with the same name already exists.",
    )]

    def _auto_init(self):
        super()._auto_init()
        # Update the generic unique name constraint to not consider the purchases in latam companies.
        # The name should be unique by partner for those documents.
        if not index_exists(self.env.cr, "account_move_unique_name_latam"):
            drop_index(self.env.cr, "account_move_unique_name", self._table)

            # Fixup the account.move names like "sequence (N)" removing the "(N)" part
            self.env.cr.execute("""
            UPDATE account_move SET name = SUBSTRING(account_move.name, 1, strpos(account_move.name::varchar, ' ('::varchar) -1 )
             WHERE l10n_latam_document_type_id IS NOT NULL AND account_move.name LIKE '% (%)'
               AND move_type IN ('in_invoice', 'in_refund', 'in_receipt');""")

            # Make all values of `name` different (naming them `name (1)`, `name (2)`...) so that we can add the following UNIQUE INDEX
            self.env.cr.execute("""
                WITH duplicated_sequence AS (
                    SELECT name, commercial_partner_id, l10n_latam_document_type_id, state
                      FROM account_move
                     WHERE state = 'posted'
                       AND name != '/'
                       AND (l10n_latam_document_type_id IS NOT NULL AND move_type IN ('in_invoice', 'in_refund', 'in_receipt'))
                  GROUP BY commercial_partner_id, l10n_latam_document_type_id, name, state
                    HAVING COUNT(*) > 1
                ),
                to_update AS (
                    SELECT move.id,
                           move.name,
                           move.state,
                           move.date,
                           row_number() OVER(PARTITION BY move.name, move.commercial_partner_id, move.l10n_latam_document_type_id ORDER BY move.name, move.commercial_partner_id, move.l10n_latam_document_type_id, move.date) AS row_seq
                      FROM duplicated_sequence
                      JOIN account_move move ON move.name = duplicated_sequence.name
                                            AND move.commercial_partner_id = duplicated_sequence.commercial_partner_id
                                            AND move.l10n_latam_document_type_id = duplicated_sequence.l10n_latam_document_type_id
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
                                 ON account_move(name, journal_id)
                              WHERE (state = 'posted' AND name != '/'
                                AND (l10n_latam_document_type_id IS NULL OR move_type NOT IN ('in_invoice', 'in_refund', 'in_receipt')));
                CREATE UNIQUE INDEX account_move_unique_name_latam
                                 ON account_move(name, commercial_partner_id, l10n_latam_document_type_id, company_id)
                              WHERE (state = 'posted' AND name != '/'
                                AND (l10n_latam_document_type_id IS NOT NULL AND move_type IN ('in_invoice', 'in_refund', 'in_receipt')));
            """)

    def _check_unique_vendor_number(self):
        return
