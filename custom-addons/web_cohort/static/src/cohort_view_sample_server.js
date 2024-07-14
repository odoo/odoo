/** @odoo-module */

import { parseDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { SampleServer } from "@web/model/sample_server";

/**
 * This function mocks calls to the 'get_cohort_data' method. It is
 * registered to the SampleServer's mockRegistry, so it is called with a
 * SampleServer instance as "this".
 * @private
 * @param {Object} params
 * @param {string} params.model
 * @param {Object} params.kwargs
 * @returns {Object}
 */
function _mockGetCohortData(params) {
    const { model, date_start, interval, measure, mode, timeline } = params;

    const columns_avg = {};
    const rows = [];
    let initialChurnValue = 0;

    const groups = this._mockReadGroup({
        model,
        fields: [date_start],
        groupBy: [date_start + ":" + interval],
    });
    const totalCount = groups.length;
    let totalValue = 0;
    for (const group of groups) {
        const format = SampleServer.FORMATS[interval];
        const displayFormat = SampleServer.DISPLAY_FORMATS[interval];
        const date = parseDate(group[date_start + ":" + interval], { format });
        const now = luxon.DateTime.local();
        let colStartDate = date;
        if (timeline === "backward") {
            colStartDate = colStartDate.plus({ [`${interval}s`]: -15 });
        }

        let value =
            measure === "__count"
                ? this._getRandomInt(SampleServer.MAX_INTEGER)
                : this._generateFieldValue(model, measure);
        value = value || 25;
        totalValue += value;
        let initialValue = value;
        let max = value;

        const columns = [];
        for (let column = 0; column <= 15; column++) {
            if (!columns_avg[column]) {
                columns_avg[column] = { percentage: 0, count: 0 };
            }
            if (colStartDate.plus({ [`${interval}s`]: column }) > now) {
                columns.push({ value: "-", churn_value: "-", percentage: "" });
                continue;
            }
            let colValue = 0;
            if (max > 0) {
                colValue = Math.min(Math.round(Math.random() * max), max);
                max -= colValue;
            }
            if (timeline === "backward" && column === 0) {
                initialValue = Math.min(Math.round(Math.random() * value), value);
                initialChurnValue = value - initialValue;
            }
            const previousValue = column === 0 ? initialValue : columns[column - 1].value;
            const remainingValue = previousValue - colValue;
            const previousChurnValue =
                column === 0 ? initialChurnValue : columns[column - 1].churn_value;
            const churn_value = colValue + previousChurnValue;
            let percentage = value ? parseFloat(remainingValue / value) : 0;
            if (mode === "churn") {
                percentage = 1 - percentage;
            }
            percentage = Number((100 * percentage).toFixed(1));
            columns_avg[column].percentage += percentage;
            columns_avg[column].count += 1;
            columns.push({
                value: remainingValue,
                churn_value,
                percentage,
                period: column, // used as a t-key but we don't care about value itself
            });
        }
        const keepRow = columns.some((c) => c.percentage !== "");
        if (keepRow) {
            rows.push({ date: date.toFormat(displayFormat), value, columns });
        }
    }
    const avg_value = totalCount ? totalValue / totalCount : 0;
    const avg = { avg_value, columns_avg };
    return { rows, avg };
}

registry.category("sample_server").add("get_cohort_data", _mockGetCohortData);
