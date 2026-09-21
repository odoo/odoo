MODULE = "pos_account_reports"


def migrate(cr, version):
    if not version:
        return
    # The module held one test and no data; the test now lives in point_of_sale/tests.
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = %s OR (module = 'base' AND name = %s)",
        (MODULE, f"module_{MODULE}"),
    )
    cr.execute("DELETE FROM ir_module_module_dependency WHERE name = %s", (MODULE,))
    cr.execute("DELETE FROM ir_module_module WHERE name = %s", (MODULE,))
