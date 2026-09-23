RENAMED_VIEWS = [
    "res_config_settings_view_form",
    "setup_financial_year_opening_form",
    "view_account_form",
    "view_company_form",
]


def migrate(cr, version):
    if not version:
        return

    # account_reports 1.1 suffixed these four to clear a collision with account's own
    # ids. A database that never ran that migration upgrades straight into the fold, so
    # apply it here too; it is a no-op where 1.1 already ran.
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = name || '_reports'
         WHERE module = 'account_reports'
           AND model = 'ir.ui.view'
           AND name = ANY(%s)
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data d
                WHERE d.module = 'account_reports'
                  AND d.name = ir_model_data.name || '_reports'
           )
        """,
        [RENAMED_VIEWS],
    )

    # Both modules reflected the same ir.model and ir.model.fields rows, so each holds its
    # own xmlid pointing at the identical record -- 63 of them on a database carrying both.
    # Those are duplicates, not conflicts: drop account_reports' copy, account already owns
    # the same name against the same res_id.
    cr.execute(
        """
        DELETE FROM ir_model_data r
         USING ir_model_data a
         WHERE r.module = 'account_reports'
           AND a.module = 'account'
           AND a.name = r.name
           AND a.model = r.model
           AND a.res_id = r.res_id
        """
    )

    # Anything still sharing a name now points at a DIFFERENT record, which is a real
    # conflict. Stop before writing rather than after: ir_model_data is UNIQUE (module,
    # name), so letting it run would abort with a constraint error naming no ids at all.
    cr.execute(
        """
        SELECT r.model, r.name
          FROM ir_model_data r
          JOIN ir_model_data a ON a.module = 'account' AND a.name = r.name
         WHERE r.module = 'account_reports'
        """
    )
    if collisions := cr.fetchall():
        raise ValueError(
            f"account_reports cannot fold into account: {len(collisions)} xmlid(s) name "
            "different records in each, rename them before upgrading -- "
            + ", ".join(f"{m}:{n}" for m, n in collisions[:20])
        )

    # Repoint, never delete. An xmlid whose module no longer declares it is reaped and the
    # record behind it destroyed; ir_ui_view_custom.ref_id alone is CASCADE, so that would
    # silently delete every user's view customisation. Moving the row keeps every record id.
    cr.execute(
        "UPDATE ir_model_data SET module = 'account' WHERE module = 'account_reports'"
    )

    # The module is absorbed, not renamed, so its own row and the dependency edges naming
    # it are now phantoms -- the 120 dependents' manifests name `account` instead. Left in
    # place they keep the module reading `installed` with nothing on disk behind it.
    # Stored arches and stored expressions still spell the old module. Repointing the
    # ir_model_data rows above makes `account_reports.x` unresolvable, and a view whose
    # arch still names it fails validation BEFORE the upgrade can load the corrected
    # source -- so the rewrite has to happen here, in the same pre-migration. \y is a word
    # boundary, which keeps account_reports_cash_basis and the _account_reports_* method
    # names out of it.
    OLD = r"\yaccount_reports\."
    for table, columns in (
        ("ir_ui_view", ("arch_db",)),
        ("ir_act_window", ("domain", "context")),
        ("ir_act_server", ("code",)),
        ("ir_filters", ("domain", "context")),
    ):
        for column in columns:
            cast = "::text" if (table, column) == ("ir_ui_view", "arch_db") else ""
            back = "::jsonb" if cast else ""
            cr.execute(
                f"""
                UPDATE {table}
                   SET {column} = regexp_replace(
                           {column}{cast}, %s, 'account.', 'g'
                       ){back}
                 WHERE {column}{cast} ~ %s
                """,
                (OLD, OLD),
            )

    cr.execute("DELETE FROM ir_module_module_dependency WHERE name = 'account_reports'")
    cr.execute("DELETE FROM ir_module_module WHERE name = 'account_reports'")
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'base' AND name = 'module_account_reports'"
    )
