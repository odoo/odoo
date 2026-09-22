/** @odoo-module native */
// @ts-check

import { EvaluationError } from "@odoo/o-spreadsheet";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { _t } from "@web/core/translation";

/**
 * @typedef {import("@spreadsheet/helpers/period").DateRange} DateRange
 */

export class ReportFormulaPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ (["getReportValue"]);

    constructor(config) {
        super(config);
        /** @type {import("@spreadsheet/data_sources/server_data").ServerData} */
        this._serverData = config.custom.odooDataProvider?.serverData;
    }

    get serverData() {
        if (!this._serverData) {
            throw new Error(
                "'serverData' is not defined, please make sure a 'OdooDataProvider' instance is provided to the model.",
            );
        }
        return this._serverData;
    }

    /**
     * @param {string | number} report xmlid or id of the report
     * @param {string} lineCode code of the report line
     * @param {string} label expression label of the column
     * @param {DateRange} dateRange
     * @param {number | null} companyId
     * @param {boolean} includeUnposted
     * @returns {number}
     */
    getReportValue(report, lineCode, label, dateRange, companyId, includeUnposted) {
        // Excel dates start at 1899-12-30; a year this low raises server side.
        if (dateRange.year < 1900) {
            throw new EvaluationError(_t("%s is not a valid year.", dateRange.year));
        }
        const result = this.serverData.batch.get(
            "report.formula",
            "spreadsheet_fetch_report_values",
            camelToSnakeObject({
                report,
                lineCode,
                label,
                dateRange,
                companyId,
                includeUnposted,
            }),
        );
        if (result === false) {
            throw new EvaluationError(
                _t("Report %(report)s has no line %(line)s with a column %(label)s.", {
                    report,
                    line: lineCode,
                    label,
                }),
            );
        }
        return result.value;
    }
}
