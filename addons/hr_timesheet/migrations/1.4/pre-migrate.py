def migrate(cr, version):
    if not version:
        return
    # The ORM inlines _table_query; the view init() used to create is read by nothing.
    cr.execute("DROP VIEW IF EXISTS timesheets_analysis_report CASCADE")
