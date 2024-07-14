/** @odoo-module **/

import { parseDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

/**
 * @private
 * @param {string} model
 * @param {Object} kwargs
 * @returns {Promise}
 */
function _mockGetCohortData(route, args) {
    const model = args.model;
    const kwargs = args.kwargs;
    const displayFormats = {
        day: "dd MM yyyy",
        week: "WW kkkk",
        month: "MMMM yyyy",
        year: "y",
    };
    const rows = [];
    let totalValue = 0;
    let initialChurnValue = 0;
    const columnsAvg = {};

    const groups = this.mockReadGroup(model, {
        domain: kwargs.domain,
        fields: [kwargs.date_start],
        groupby: [kwargs.date_start + ":" + kwargs.interval],
    });
    const totalCount = groups.length;
    for (const group of groups) {
        let format;
        switch (kwargs.interval) {
            case "day":
                format = "yyyy-MM-dd";
                break;
            case "week":
                format = "WW kkkk";
                break;
            case "month":
                format = "MMMM yyyy";
                break;
            case "year":
                format = "y";
                break;
        }
        const cohortStartDate = parseDate(group[kwargs.date_start + ":" + kwargs.interval], {
            format,
        });

        const records = this.mockSearchController({
            model: model,
            domain: group.__domain,
        });
        let value = 0;
        if (kwargs.measure === "__count") {
            value = records.length;
        } else {
            if (records.length) {
                value = records.records
                    .map((r) => r[kwargs.measure])
                    .reduce(function (a, b) {
                        return a + b;
                    });
            }
        }
        totalValue += value;
        let initialValue = value;

        const columns = [];
        let colStartDate = cohortStartDate;
        if (kwargs.timeline === "backward") {
            colStartDate = colStartDate.plus({ [`${kwargs.interval}s`]: -15 });
        }
        for (let column = 0; column <= 15; column++) {
            if (!columnsAvg[column]) {
                columnsAvg[column] = { percentage: 0, count: 0 };
            }
            if (column !== 0) {
                colStartDate = colStartDate.plus({ [`${kwargs.interval}s`]: 1 });
            }
            if (colStartDate > luxon.DateTime.local()) {
                columnsAvg[column]["percentage"] += 0;
                columnsAvg[column]["count"] += 0;
                columns.push({
                    value: "-",
                    churn_value: "-",
                    percentage: "",
                });
                continue;
            }

            const compareDate = colStartDate.toFormat(displayFormats[kwargs.interval]);
            let colRecords = records.records.filter((record) => {
                return (
                    record[kwargs.date_stop] &&
                    parseDate(record[kwargs.date_stop], { format: "yyyy-MM-dd" }).toFormat(
                        displayFormats[kwargs.interval]
                    ) == compareDate
                );
            });
            let colValue = 0;
            if (kwargs.measure === "__count") {
                colValue = colRecords.length;
            } else {
                if (colRecords.length) {
                    colValue = colRecords
                        .map((x) => x[kwargs.measure])
                        .reduce(function (a, b) {
                            return a + b;
                        });
                }
            }

            if (kwargs.timeline === "backward" && column === 0) {
                colRecords = records.records.filter((record) => {
                    return (
                        record[kwargs.date_stop] &&
                        parseDate(record[kwargs.date_stop], { format: "yyyy-MM-dd" }) >=
                            colStartDate
                    );
                });
                if (kwargs.measure === "__count") {
                    initialValue = colRecords.length;
                } else {
                    if (colRecords.length) {
                        initialValue = colRecords
                            .map((x) => x[kwargs.measure])
                            .reduce((a, b) => {
                                return a + b;
                            });
                    }
                }
                initialChurnValue = value - initialValue;
            }
            const previousValue = column === 0 ? initialValue : columns[column - 1]["value"];
            const remainingValue = previousValue - colValue;
            const previousChurnValue =
                column === 0 ? initialChurnValue : columns[column - 1]["churn_value"];
            const churnValue = colValue + previousChurnValue;
            let percentage = value ? parseFloat(remainingValue / value) : 0;
            if (kwargs.mode === "churn") {
                percentage = 1 - percentage;
            }
            percentage = Number((100 * percentage).toFixed(1));
            columnsAvg[column]["percentage"] += percentage;
            columnsAvg[column]["count"] += 1;
            columns.push({
                value: remainingValue,
                churn_value: churnValue,
                percentage: percentage,
                domain: [],
                period: compareDate,
            });
        }
        rows.push({
            date: cohortStartDate.toFormat(displayFormats[kwargs.interval]),
            value: value,
            domain: group.__domain,
            columns: columns,
        });
    }

    return Promise.resolve({
        rows: rows,
        avg: {
            avg_value: totalCount ? totalValue / totalCount : 0,
            columns_avg: columnsAvg,
        },
    });
}

registry.category("mock_server").add("get_cohort_data", _mockGetCohortData);
