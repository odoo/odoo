def migrate(cr, version):
    if not version:
        return
    # the three multi-company rules move here from account with the models they guard;
    # re-homing the external ids keeps the records instead of deleting and recreating them
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'account_tax'
         WHERE module = 'account'
           AND model = 'ir.rule'
           AND name = ANY(%s)
        """,
        [["tax_group_comp_rule", "tax_comp_rule", "tax_rep_comp_rule"]],
    )
