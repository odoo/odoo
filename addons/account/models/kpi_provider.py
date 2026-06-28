from odoo import api, models
from odoo.tools import SQL


class KpiProvider(models.AbstractModel):
    _inherit = 'kpi.provider'

    @api.model
    def get_account_kpi_summary(self):
        return get_kpi_summary(self.env.cr, self.env.uid)

    @api.model
    def get_kpi_summary(self):
        result = super().get_kpi_summary()
        result.extend(self.get_account_kpi_summary())
        return result


def get_kpi_summary(cr, uid):
    """
    Retrieve the number of account moves per journal type requiring user attention.

    The counted account moves include:
    - draft journal entries;
    - posted journal entries that are not checked;
    - posted bank journal entries that are not yet reconciled.

    This function intentionally bypasses the ORM so KPI summaries can be retrieved
    without loading a registry, allowing multi-database servers to serve them faster.
    """
    expected_columns = {
        'account_bank_statement_line.is_reconciled',
        'account_move.review_state',
        'account_move.journal_id',
        'account_move.state',
        'account_move.statement_line_id',
        'account_journal.type',
    }
    cr.execute(SQL("""
        SELECT table_name || '.' || column_name
          FROM information_schema.columns
         WHERE table_name || '.' || column_name IN %(columns)s
    """, columns=tuple(expected_columns)))
    existing_columns = {x[0] for x in cr.fetchall()}
    if expected_columns - existing_columns:
        # Needed columns are not present -> module is not installed
        return []

    cr.execute(SQL("""
        WITH journal_type_selection AS (
            SELECT selection.value, COALESCE(selection.name->>p.lang, selection.name->>'en_US') name
              FROM ir_model_fields_selection selection
              JOIN ir_model_fields field ON selection.field_id = field.id
              JOIN res_users u ON u.id = %(uid)s
              JOIN res_partner p ON u.partner_id = p.id
             WHERE field.model = 'account.journal'
               AND field.name = 'type'
        )
        SELECT journal.type,
               COALESCE(journal_type_selection.name, journal.type),
               COUNT(*)
          FROM account_move move
          JOIN account_journal journal ON move.journal_id = journal.id
     LEFT JOIN account_bank_statement_line st_line ON move.statement_line_id = st_line.id
     LEFT JOIN journal_type_selection ON journal_type_selection.value = journal.type
         WHERE (   move.state = 'draft'
                OR (    move.state = 'posted'
                    AND move.review_state IN ('todo', 'anomaly'))
                OR (    move.state = 'posted'
                    AND journal.type = 'bank'
                    AND (st_line.id IS NULL OR NOT st_line.is_reconciled)))
      GROUP BY journal.type, journal_type_selection.name
    """, uid=uid))

    return [{
        'id': f'account_journal_type.{journal_type}',
        'name': journal_type_name,
        'type': 'integer',
        'value': count,
    } for journal_type, journal_type_name, count in cr.fetchall()]
