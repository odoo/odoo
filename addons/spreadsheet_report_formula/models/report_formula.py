import calendar
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ReportFormula(models.Model):
    _inherit = "report.formula"

    def _get_spreadsheet_period_bounds(self, period):
        range_type = period["range_type"]
        year = period["year"]
        if range_type == "year":
            last_day, last_month = self._get_year_end()
            if (last_day, last_month) != (31, 12):
                year += 1
            year_end = date(
                year,
                last_month,
                min(last_day, calendar.monthrange(year, last_month)[1]),
            )
            bounds = self._get_year_bounds(year_end)
            return bounds["date_from"], bounds["date_to"]
        if range_type == "quarter":
            start = date(year, period["quarter"] * 3 - 2, 1)
            return start, start + relativedelta(months=3, days=-1)
        if range_type == "month":
            start = date(year, period["month"], 1)
            return start, start + relativedelta(months=1, days=-1)
        end = date(year, period["month"], period["day"])
        return self._get_year_bounds(end)["date_from"], end

    @api.model
    def _get_spreadsheet_report(self, reference):
        if isinstance(reference, int) or str(reference).isdigit():
            return self.browse(int(reference)).exists()
        record = self.env.ref(str(reference), raise_if_not_found=False)
        return record if record and record._name == self._name else self.browse()

    @api.readonly
    @api.model
    def spreadsheet_fetch_report_values(self, args_list):
        """Fetch data for ODOO.REPORT formulas.
        The input list looks like this::

            [
                {
                    report: str(xmlid) | int,
                    line_code: str,
                    label: str,
                    date_range: {range_type: "year", year: int},
                    company_id: int | None,
                    include_unposted: bool,
                }
            ]

        A formula whose report or line does not exist gets ``False``.
        """
        results = [False] * len(args_list)
        requests = defaultdict(list)
        for index, args in enumerate(args_list):
            report = self._get_spreadsheet_report(args["report"])
            if not report:
                continue
            company_id = args.get("company_id") or self.env.company.id
            date_from, date_to = report.with_company(
                company_id
            )._get_spreadsheet_period_bounds(args["date_range"])
            key = (
                report.id,
                company_id,
                date_from,
                date_to,
                bool(args.get("include_unposted")),
            )
            requests[key].append(index)

        for key, indexes in requests.items():
            report_id, company_id, date_from, date_to, include_unposted = key
            report = self.browse(report_id).with_company(company_id)
            options = report.get_options(
                {
                    "selected_variant_id": report.id,
                    "date": {
                        "date_from": fields.Date.to_string(date_from),
                        "date_to": fields.Date.to_string(date_to),
                        "mode": "range",
                        "filter": "custom",
                    },
                    "all_entries": include_unposted,
                }
            )
            values = {
                (expression.report_line_id.code, expression.label): value
                for expression, value in report._get_expression_values(options).items()
            }
            for index in indexes:
                args = args_list[index]
                key = (args["line_code"], args["label"])
                if key in values:
                    results[index] = {"value": values[key] or 0.0}
        return results
