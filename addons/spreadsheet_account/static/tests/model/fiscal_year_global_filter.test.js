/** @ts-check */
import { describe, expect, test } from "@odoo/hoot";
import { Model } from "@odoo/o-spreadsheet";
import {
    dateFilterValueToString,
    getDateRange,
    getNextDateFilterValue,
    getPreviousDateFilterValue,
} from "@spreadsheet/global_filters/helpers";

const { DateTime } = luxon;

describe.current.tags("headless");

const modelConfig = {
    custom: {
        currentFiscalYearStart: DateTime.fromISO("2022-07-01"),
        currentFiscalYearEnd: DateTime.fromISO("2023-06-30"),
    },
};

test("fiscal_year global filter", () => {
    const model = new Model({}, modelConfig);
    const now = DateTime.fromISO("2022-10-16");
    const filterValue = { type: "fiscal_year", offset: 0 };

    let { from, to } = getDateRange(filterValue, 0, now, model.getters);
    expect(from.toISODate()).toBe("2022-07-01");
    expect(to.toISODate()).toBe("2023-06-30");
    expect(dateFilterValueToString(filterValue, model.getters)).toBe("2022-2023");

    const nextValue = getNextDateFilterValue(filterValue);
    expect(nextValue).toEqual({ type: "fiscal_year", offset: 1 });
    ({ from, to } = getDateRange(nextValue, 0, now, model.getters));
    expect(from.toISODate()).toBe("2023-07-01");
    expect(to.toISODate()).toBe("2024-06-30");
    expect(dateFilterValueToString(nextValue, model.getters)).toBe("2023-2024");

    const previousValue = getPreviousDateFilterValue(filterValue);
    expect(previousValue).toEqual({ type: "fiscal_year", offset: -1 });
    ({ from, to } = getDateRange(previousValue, 0, now, model.getters));
    expect(from.toISODate()).toBe("2021-07-01");
    expect(to.toISODate()).toBe("2022-06-30");
    expect(dateFilterValueToString(previousValue, model.getters)).toBe("2021-2022");
});

test("Data source offset is applied to fiscal_year global filter", () => {
    const model = new Model({}, modelConfig);
    const now = DateTime.fromISO("2022-10-16");
    const filterValue = { type: "fiscal_year", offset: 1 };
    let dataSourceOffset = 2;

    let { from, to } = getDateRange(filterValue, dataSourceOffset, now, model.getters);
    expect(from.toISODate()).toBe("2025-07-01"); // 2022 + 1 + 2
    expect(to.toISODate()).toBe("2026-06-30");

    dataSourceOffset = -1;
    ({ from, to } = getDateRange(filterValue, dataSourceOffset, now, model.getters));
    expect(from.toISODate()).toBe("2022-07-01"); // 2022 + 1 - 1
    expect(to.toISODate()).toBe("2023-06-30");
});

test("this_fiscal_year global filter", () => {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "date",
                label: "This Fiscal Year",
                defaultValue: "this_fiscal_year",
            },
        ],
    };
    const model = new Model(spreadsheetData, modelConfig);
    expect(model.getters.getGlobalFilterValue("1")).toEqual({ type: "fiscal_year", offset: 0 });
});
