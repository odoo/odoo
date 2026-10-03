from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for report_xml_id in ('l10n_in.tcs_report', 'l10n_in.tds_report'):
        report = env.ref(report_xml_id, raise_if_not_found=False)
        if report:
            report.active_fallback = True
