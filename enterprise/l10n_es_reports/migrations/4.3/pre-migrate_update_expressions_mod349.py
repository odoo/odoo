def migrate(cr, version):
    account_report_lines = (
        'mod_349_supplies',
        'mod_349_acquisitions',
        'mod_349_triangular',
        'mod_349_services_sold',
        'mod_349_services_acquired',
        'mod_349_supplies_without_taxes',
        'mod_349_supplies_without_taxes_legal_representative',
        'mod_349_supplies_refunds',
        'mod_349_acquisitions_refunds',
        'mod_349_triangular_refunds',
        'mod_349_services_sold_refunds',
        'mod_349_services_acquired_refunds',
        'mod_349_supplies_without_taxes_refunds',
        'mod_349_supplies_without_taxes_legal_representative_refunds'
    )
    cr.execute(
        """
            DELETE FROM account_report_expression AS expression_delete
                  USING account_report_expression expression
                   JOIN account_report_line line
                     ON expression.report_line_id = line.id
                   JOIN ir_model_data imd_line
                     ON line.id = imd_line.res_id
                    AND imd_line.model = 'account.report.line'
              LEFT JOIN ir_model_data imd_expression
                     ON expression.id = imd_expression.res_id
                    AND imd_expression.model = 'account.report.expression'
                  WHERE expression.engine = 'domain'
                    AND expression.label = 'balance'
                    AND imd_expression.id IS NULL
                    AND imd_line.name IN %s
                    AND expression_delete.id = expression.id
        """,
        [account_report_lines]
    )
