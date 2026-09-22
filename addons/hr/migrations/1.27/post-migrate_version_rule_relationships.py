OLD_DOMAIN = "[('company_id', 'in', company_ids + [False])]"
NEW_DOMAIN = """['|', '|', '|',
            ('company_id', 'in', company_ids + [False]),
            ('employee_id.parent_id.user_id', '=', user.id),
            ('employee_id', '=', user.employee_id.parent_id.id),
            ('employee_id.user_id', '=', user.id)
        ]"""


def migrate(cr, version):
    if not version:
        return
    # the employee's rule lets a user read their manager, their reports and
    # themselves in another company; hr.employee now binds hr.version's rule
    # through version_id, so the version grants the same relationships. A
    # domain edited on the database is left as its owner wrote it
    cr.execute(
        """
        UPDATE ir_rule r
           SET domain_force = %s
          FROM ir_model_data d
         WHERE d.model = 'ir.rule'
           AND d.module = 'hr'
           AND d.name = 'ir_rule_hr_contract_multi_company'
           AND d.res_id = r.id
           AND r.domain_force = %s
        """,
        (NEW_DOMAIN, OLD_DOMAIN),
    )
