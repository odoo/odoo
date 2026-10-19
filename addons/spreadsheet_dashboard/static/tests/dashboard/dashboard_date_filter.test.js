import { describe, expect, test } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { DashboardDateFilter } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_date_filter/dashboard_date_filter";
import { Model } from "@odoo/o-spreadsheet";

describe.current.tags("desktop");
defineSpreadsheetModels();

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountDashboardFilterValue(props) {
    const model = new Model();
    await mountWithCleanup(DashboardDateFilter, { props: { model, ...props } });
}

test("Can display the input as a button", async function () {
    await mountDashboardFilterValue({
        value: { type: "range", from: "2023-01-01", to: "2023-01-31" },
        update: () => {},
    });
    expect("button").toHaveCount(3);
    expect(".o-date-filter-value").toHaveText(/January 1\s–\s31, 2023/);
});

test("Can navigate with buttons to select the next period", async function () {
    await mountDashboardFilterValue({
        value: { type: "month", month: 1, year: 2023 },
        update: (value) => {
            expect.step("update");
            expect(value).toEqual({ type: "month", month: 2, year: 2023 });
        },
    });
    await contains(".btn-next-date").click();
    expect.verifySteps(["update"]);
});

test("Can navigate with buttons to select the previous period", async function () {
    await mountDashboardFilterValue({
        value: { type: "month", month: 1, year: 2023 },
        update: (value) => {
            expect.step("update");
            expect(value).toEqual({ type: "month", month: 12, year: 2022 });
        },
    });
    await contains(".btn-previous-date").click();
    expect.verifySteps(["update"]);
});
