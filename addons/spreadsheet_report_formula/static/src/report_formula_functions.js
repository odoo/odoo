/** @odoo-module native */
import * as spreadsheet from "@odoo/o-spreadsheet";
import { parsePeriod } from "@spreadsheet/helpers/period";
import { _t } from "@web/core/translation";

import { ReportFormulaPlugin } from "./plugins/report_formula_plugin.js";

const { functionRegistry, featurePluginRegistry } = spreadsheet.registries;
const { arg, toBoolean, toString, toNumber } = spreadsheet.helpers;

featurePluginRegistry.add("odooReportFormula", ReportFormulaPlugin);

functionRegistry.add("ODOO.REPORT", {
    description: _t(
        "Get the figure a report shows for one of its lines and columns over a period.",
    ),
    args: [
        arg(
            "report (string)",
            _t('The report, by external id (e.g. "account.profit_and_loss") or id.'),
        ),
        arg("line_code (string)", _t("The code of the report line.")),
        arg("column (string)", _t('The column label (e.g. "balance").')),
        arg(
            "date_range (string, date)",
            _t(
                `The date range. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`,
            ),
        ),
        arg("offset (number, default=0)", _t("Offset applied to the years.")),
        arg("company_id (number, optional)", _t("The company to target (Advanced).")),
        arg(
            "include_unposted (boolean, default=FALSE)",
            _t("Set to TRUE to include unposted entries."),
        ),
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        report,
        lineCode,
        column,
        dateRange,
        offset = { value: 0 },
        companyId = { value: null },
        includeUnposted = { value: false },
    ) {
        const _dateRange = parsePeriod(dateRange, this.locale);
        _dateRange.year += toNumber(offset, this.locale);
        const _report = toString(report).trim();
        const _companyId = companyId?.value;
        return {
            value: this.getters.getReportValue(
                /^\d+$/.test(_report) ? Number(_report) : _report,
                toString(lineCode).trim(),
                toString(column).trim(),
                _dateRange,
                _companyId,
                toBoolean(includeUnposted),
            ),
            format: this.getters.getCompanyCurrencyFormat(_companyId) || "#,##0.00",
        };
    },
});
