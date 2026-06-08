import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import {
    defineSpreadsheetDashboardModels,
    SpreadsheetDashboard,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

const THIS_FISCAL_YEAR_FILTER = {
    id: "1",
    type: "date",
    label: "This Fiscal Year",
    defaultValue: "this_fiscal_year",
};

let fiscalYearStart = "2025-07-01";
let fiscalYearEnd = "2026-06-30";

let spreadsheetData;
beforeEach(() => {
    spreadsheetData = undefined;
    fiscalYearStart = "2025-07-01";
    fiscalYearEnd = "2026-06-30";
    onRpc(
        "/spreadsheet/dashboard/data/1",
        () => ({
            snapshot: spreadsheetData,
            revisions: [],
            current_fiscal_year_start: fiscalYearStart,
            current_fiscal_year_end: fiscalYearEnd,
        }),
        { pure: true }
    );
});

test("Can navigate in a fiscal year global filter", async function () {
    spreadsheetData = { globalFilters: [THIS_FISCAL_YEAR_FILTER] };
    SpreadsheetDashboard._records[0].spreadsheet_data = JSON.stringify(spreadsheetData);
    const { model } = await createSpreadsheetDashboard({});

    expect(".o-date-filter-value").toHaveText("2025-2026");
    expect(model.getters.getGlobalFilterValue("1")).toEqual({ type: "fiscal_year", offset: 0 });

    await contains(".btn-previous-date").click();
    expect(".o-date-filter-value").toHaveText("2024-2025");
    expect(model.getters.getGlobalFilterValue("1")).toEqual({ type: "fiscal_year", offset: -1 });

    await contains(".btn-next-date").click();
    expect(".o-date-filter-value").toHaveText("2025-2026");
    expect(model.getters.getGlobalFilterValue("1")).toEqual({ type: "fiscal_year", offset: 0 });

    await contains(".btn-next-date").click();
    expect(".o-date-filter-value").toHaveText("2026-2027");
    expect(model.getters.getGlobalFilterValue("1")).toEqual({ type: "fiscal_year", offset: 1 });
});

test("Can navigate in a fiscal year global filter in the dropdown", async function () {
    spreadsheetData = { globalFilters: [THIS_FISCAL_YEAR_FILTER] };
    SpreadsheetDashboard._records[0].spreadsheet_data = JSON.stringify(spreadsheetData);
    const { model } = await createSpreadsheetDashboard({});
    const fixture = getFixture();

    function getCustomRangeValue() {
        const inputs = fixture.querySelectorAll(".o-dropdown-item[data-id='range'] input");
        return [...inputs].map((input) => input.value);
    }

    await contains(".o-date-filter-value").click();

    expect(".o-dropdown-item[data-id='fiscal_year']").toHaveClass("selected");
    expect(getCustomRangeValue()).toEqual(["07/01/2025", "06/30/2026"]);

    await contains(".o-dropdown-item[data-id='fiscal_year'] .btn-next").click();
    expect(".o-dropdown-item[data-id='fiscal_year']").toHaveClass("selected");
    expect(getCustomRangeValue()).toEqual(["07/01/2026", "06/30/2027"]);
    expect(model.getters.getGlobalFilterValue("1")).toEqual({ type: "fiscal_year", offset: 1 });
});

test("Fiscal year filter is hidden in dropdown if the fiscal year the same as the normal year", async function () {
    fiscalYearStart = "2025-01-01";
    fiscalYearEnd = "2025-12-31";
    spreadsheetData = { globalFilters: [THIS_FISCAL_YEAR_FILTER] };
    SpreadsheetDashboard._records[0].spreadsheet_data = JSON.stringify(spreadsheetData);
    await createSpreadsheetDashboard({});
    await contains(".o-date-filter-value").click();

    expect(".o-dropdown-item[data-id='fiscal_year']").toHaveCount(0);
});
