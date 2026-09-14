def _fill_flow_state(cr):
    cr.execute(
        "ALTER TABLE approval_approver ADD COLUMN IF NOT EXISTS flow_state varchar"
    )
    cr.execute(
        """
        UPDATE approval_approver
           SET flow_state = CASE
                   WHEN state IN ('new', 'pending', 'waiting', 'cancelled') THEN state
                   WHEN state = 'refused' AND decision_date IS NULL THEN 'refused'
                   ELSE 'waiting'
               END
         WHERE flow_state IS NULL
        """
    )


def migrate(cr, version):
    # The ledger backfill lives in post-migrate.py: approval.decision.log was
    # born in 19.0.2.1.0, and a pre-migration runs before the models load, so a
    # database jumping here from below 2.1 has no ledger table yet to read.
    _fill_flow_state(cr)
