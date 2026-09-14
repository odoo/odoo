"""The presence evidence stops being four same-day booleans reset by the cron.

Two of them recorded evidence (an IP connection, enough emails sent) and two
encoded one tri-state override; all four were true only until the next hourly
sweep, and only for the one company the cron user happened to sit in. They
become dates in the employee's own timezone, so a company the sweep never
reaches cannot leave yesterday's evidence standing.

The IP evidence also stops living in `res.users.log`. That table's contract is
one surviving row per user -- `base` vacuums the rest nightly to keep
`res.users.login_date` meaningful -- so the rows this module wrote were both
destroying that field and being destroyed by it.
"""


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE hr_employee
            ADD COLUMN IF NOT EXISTS hr_presence_ip_date date,
            ADD COLUMN IF NOT EXISTS hr_presence_email_date date,
            ADD COLUMN IF NOT EXISTS hr_presence_manual_state varchar,
            ADD COLUMN IF NOT EXISTS hr_presence_manual_date date
    """)
    cr.execute("""
        UPDATE hr_employee
           SET hr_presence_ip_date = CASE WHEN ip_connected THEN CURRENT_DATE END,
               hr_presence_email_date = CASE WHEN email_sent THEN CURRENT_DATE END,
               hr_presence_manual_state = CASE
                   WHEN NOT manually_set_presence THEN NULL
                   WHEN manually_set_present THEN 'present'
                   ELSE 'absent'
               END,
               hr_presence_manual_date = CASE
                   WHEN manually_set_presence THEN CURRENT_DATE
               END
    """)
    cr.execute("""
        ALTER TABLE hr_employee
            DROP COLUMN IF EXISTS email_sent,
            DROP COLUMN IF EXISTS ip_connected,
            DROP COLUMN IF EXISTS manually_set_present,
            DROP COLUMN IF EXISTS manually_set_presence
    """)

    # hr_presence_last_compute_date guarded "is this evidence from today"; the
    # evidence carries its own date now, and ir.cron.lastcall already records
    # when the sweep ran.
    cr.execute("""
        ALTER TABLE res_company DROP COLUMN IF EXISTS hr_presence_last_compute_date
    """)
    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model = 'res.company' AND name = 'hr_presence_last_compute_date'
    """)

    # The presence pings this module wrote into res.users.log are what made
    # res.users.login_date report a heartbeat instead of a login.
    cr.execute("DELETE FROM res_users_log WHERE ip IS NOT NULL")
    cr.execute("ALTER TABLE res_users_log DROP COLUMN IF EXISTS ip")
    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model = 'res.users.log' AND name = 'ip'
    """)

    # The code referenced hr_presence.sms_template_presence; the data file
    # shipped the same record as sms_template_data_hr_presence, so the template
    # was never found and every SMS fell back to a hardcoded body.
    cr.execute("""
        UPDATE ir_model_data
           SET name = 'sms_template_presence'
         WHERE module = 'hr_presence'
           AND name = 'sms_template_data_hr_presence'
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data existing
                WHERE existing.module = 'hr_presence'
                  AND existing.name = 'sms_template_presence'
           )
    """)
