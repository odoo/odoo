MOVED_MODELS = (
    "account.report",
    "account.report.line",
    "account.report.expression",
    "account.report.column",
    "account.report.external.value",
)


def migrate(cr, version):
    if not version:
        return
    # Fields of the report models move from account down to report_formula, which
    # `-u account` does not upgrade: it never reflects them, so at the end of this
    # upgrade account's xmlid is the only one naming the field, it is stale, and
    # the field goes -- with its column. Measured: account_report.
    # custom_handler_model_id was dropped. Give report_formula a twin of every
    # such xmlid first. A twin on a field account still owns is dropped as stale
    # by report_formula's next upgrade, and the record stays: account names it.
    cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        SELECT 'report_formula', d.name, d.model, d.res_id, d.noupdate
          FROM ir_model_data d
          JOIN ir_model_fields f ON f.id = d.res_id
         WHERE d.module = 'account'
           AND d.model = 'ir.model.fields'
           AND f.model = ANY(%s)
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data t
                WHERE t.module = 'report_formula' AND t.name = d.name)
        """,
        [list(MOVED_MODELS)],
    )
