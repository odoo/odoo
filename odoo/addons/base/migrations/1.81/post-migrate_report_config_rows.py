from odoo.db.schema import column_exists


def migrate(cr, version):
    if not version or not column_exists(cr, "res_company", "report_header"):
        return
    cr.execute(
        """
        INSERT INTO report_config (company_id, report_header, report_footer, company_details,
                                   paperformat_id, create_uid, create_date, write_uid, write_date)
             SELECT c.id, c.report_header, c.report_footer, c.company_details, c.paperformat_id,
                    1, now() at time zone 'UTC', 1, now() at time zone 'UTC'
               FROM res_company c
              WHERE NOT EXISTS (SELECT 1 FROM report_config rc WHERE rc.company_id = c.id)
        """
    )
