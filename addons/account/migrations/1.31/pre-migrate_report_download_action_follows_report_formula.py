MOVED_MODEL = "ir_actions_account_report_download"


def migrate(cr, version):
    if not version:
        return
    # Same reason as 1.29: report_formula is a dependency `-u account` does not
    # reload, so without a second xmlid the model's ir.model row and its fields
    # are account's orphans at the end of this upgrade and get deleted.
    cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        SELECT 'report_formula', d.name, d.model, d.res_id, d.noupdate
          FROM ir_model_data d
         WHERE d.module = 'account'
           AND (
                   (d.model = 'ir.model'
                    AND d.res_id IN (SELECT id FROM ir_model WHERE model = %(model)s))
                OR (d.model = 'ir.model.fields'
                    AND d.res_id IN (
                        SELECT id FROM ir_model_fields WHERE model = %(model)s))
               )
           AND NOT EXISTS (
                   SELECT 1
                     FROM ir_model_data t
                    WHERE t.module = 'report_formula'
                      AND t.name = d.name
               )
        """,
        {"model": MOVED_MODEL},
    )
