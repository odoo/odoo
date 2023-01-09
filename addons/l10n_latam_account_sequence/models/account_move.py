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
