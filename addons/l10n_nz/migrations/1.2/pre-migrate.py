def migrate(cr, version):
    cr.execute("""
        UPDATE report_formula_expression e
           SET label = '_upg_1.2balance'
          FROM ir_model_data d
         WHERE e.id = d.res_id
           AND d.module = 'l10n_nz'
           AND d.name = 'tax_report_box13_formula'
           AND e.label = 'balance'
    """)
