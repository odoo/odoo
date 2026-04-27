from dateutil.relativedelta import relativedelta
from lxml import etree
from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools import date_utils, file_open

class ItalianReportCustomHandler(models.AbstractModel):
    _name = 'l10n_it.monthly.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Italian Monthly Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault("buttons", []).append({
            "name": _("XML"),
            "sequence": 30,
            "action": "print_tax_report_to_xml",
            "file_export_type": _("XML"),
            "branch_allowed": True,
        })

    def print_tax_report_to_xml(self, options):
        view_id = self.env.ref('l10n_it_xml_export.monthly_tax_report_xml_export_wizard_view').id
        return {
            'name': _('XML Export Options'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_it_xml_export.monthly.tax.report.xml.export.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': dict(self._context, l10n_it_xml_export_monthly_tax_report_options=options),
        }

    def export_tax_report_to_xml(self, options):
        xml_export_data = self._get_xml_export_data(options)
        xml_content = self.env["ir.qweb"]._render("l10n_it_xml_export.tax_report_export_template", xml_export_data)
        xml_content = Markup("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>""") + xml_content
        xml_content = xml_content.encode()

        with file_open("l10n_it_xml_export/data/validation/fornituraIvp_2018_v1.xsd", 'rb') as xsd:
            xsd_schema = etree.XMLSchema(etree.parse(xsd))
            try:
                xsd_schema.assertValid(etree.fromstring(xml_content))
            except etree.DocumentInvalid as xml_errors:
                self.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'warning',
                        'title': _('XML Validation Error'),
                        'message': _(
                            "Some values will not pass the authority's validation, please check them before submitting your file: %s",
                            [error.path.split(":")[-1] for error in xml_errors.error_log]
                        ),
                        'sticky': True,
                    },
                )

        return {
            "file_name": f"IT{xml_export_data['taxpayer_code']}_LI_{xml_export_data['identificativo']}.xml",
            "file_content": xml_content,
            "file_type": "xml",
        }

    def _get_xml_export_data(self, options):
        options_date_to = fields.Date.from_string(options["date"]["date_to"])
        report = self.env["account.report"].browse(options["report_id"])
        company = report._get_sender_company_for_export(options)
        quarter_months = list(date_utils.date_range(*date_utils.get_quarter(options_date_to)))
        quarterly = self.env.company.account_tax_periodicity == 'trimester'
        balance_col_idx = next((idx for idx, col in enumerate(options.get('columns', [])) if col.get('expression_label') == 'balance'), None)
        report_lines_data_per_month = {date.month: {} for date in quarter_months}
        for date in quarter_months:
            date_from = date
            date_to = date_utils.end_of(date, 'month')
            at_date_options = report.get_options({
                'selected_variant_id': report.id,
                'date': {
                    'date_from': date_from,
                    'date_to': date_to,
                    'mode': 'range',
                    'filter': 'custom',
                },
            })
            at_date_report_lines = report._get_lines(at_date_options)
            at_date_report_line2amount = {
                line['columns'][balance_col_idx]['report_line_id']: (
                    f"{float(line['columns'][balance_col_idx]['no_format']):.2f}".replace(".", ",")
                    if line['columns'][balance_col_idx]['no_format'] else False
                )
                for line in at_date_report_lines
            }
            month_lines = self.env['account.report.line'].browse(at_date_report_line2amount.keys())
            month_lines.fetch(['id', 'code'])
            for report_line in month_lines:
                # VP6a and VP6b values must be absolute values.
                if report_line.code in ['VP6a', 'VP6b'] and at_date_report_line2amount.get(report_line.id) and at_date_report_line2amount[report_line.id].startswith('-'):
                    report_lines_data_per_month[date.month][report_line.code] = at_date_report_line2amount[report_line.id][1:]
                else:
                    report_lines_data_per_month[date.month][report_line.code] = at_date_report_line2amount[report_line.id]

        if quarterly:
            def to_float(val):
                if not val:
                    return 0.0
                try:
                    return float(val.replace(',', '.'))
                except (AttributeError, ValueError):
                    return 0.0

            keys = report_lines_data_per_month[quarter_months[0].month].keys()
            quarterly_totals = {
                key: sum(to_float(report_lines_data_per_month[date.month].get(key)) for date in quarter_months)
                for key in keys
            }
            report_lines_data_per_month = {
                0: {
                    key: f"{total:.2f}".replace('.', ',') if total != 0 else False
                    for key, total in quarterly_totals.items()
                }
            }

        identificativo = self.env['ir.sequence'].next_by_code('l10n_it_xml_export.identificativo')
        if not identificativo:
            self.env['ir.sequence'].create({
                'name': "IT Periodic VAT XML Export Identificativo",
                'code': "l10n_it_xml_export.identificativo",
                'padding': 5,
            })
            identificativo = self.env['ir.sequence'].next_by_code('l10n_it_xml_export.identificativo')

        return {
            "supply_code": "IVP18",
            "declarant_fiscal_code": options["declarant_fiscal_code"],
            "declarant_role_code": options["declarant_role_code"],
            "id_sistema": options["id_sistema"],
            "identificativo": identificativo,
            "taxpayer_code": company.l10n_it_codice_fiscale,
            "tax_year": options_date_to.year,
            "vat_number": "".join([char for char in report.get_vat_for_export(options) if char.isdigit()]),
            "parent_company_vat_number": options["parent_company_vat_number"],
            "last_month": (options_date_to - relativedelta(months=1)).month,
            "company_code": options["company_code"],
            "intermediary_code": options["intermediary_code"],
            "submission_commitment": options["intermediary_code"] and int(options["submission_commitment"]),
            "commitment_date": options["intermediary_code"] and fields.Date.from_string(options["commitment_date"]).strftime("%d%m%Y"),
            "intermediary_signature": options["intermediary_code"] and 1,
            "subcontracting": options["subcontracting"] and 1,
            "exceptional_events": options["exceptional_events"] and 1,
            "extraordinary_operations": options["extraordinary_operations"] and 1,
            "quarter": date_utils.get_quarter_number(options_date_to) if quarterly else 0,
            "monthly_data": {
                month: {
                    "total_active_operations": month_vals["VP2"],
                    "total_passive_operations": month_vals["VP3"],
                    "vat_payable": month_vals["VP4"],
                    "vat_deducted": month_vals["VP5"],
                    "vat_due": month_vals["VP6a"],
                    "vat_credit": month_vals["VP6b"],
                    "previous_debt": month_vals["VP7"],
                    "previous_period_credit": month_vals["VP8"],
                    "previous_year_credit": month_vals["VP9"],
                    "eu_self_payments": month_vals["VP10"],
                    "tax_credits": month_vals["VP11"],
                    "due_interests": month_vals["VP12"],
                    "method": int(options["method"]),
                    "advance_payment": month_vals["VP13"],
                    "amount_to_be_paid": month_vals["VP14a"],
                    "amount_in_credit": month_vals["VP14b"],
                } for month, month_vals in report_lines_data_per_month.items()
            }
        }
