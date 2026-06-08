import { describe, expect, test, getFixture, beforeEach } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { makeMockEnv, contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { DefaultDateValue } from "@spreadsheet/global_filters/components/default_date_value/default_date_value";

describe.current.tags("desktop");
defineSpreadsheetModels();

let fixture;

beforeEach(() => {
    fixture = getFixture();
});

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountDefaultDateValue(env, props) {
    await mountWithCleanup(DefaultDateValue, { props, env });
}

test("Default date filter without initial value", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: undefined,
        update: () => {},
    });
    expect("input").toHaveValue("All time");
});

test("Date filter with relative value", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: "last_7_days",
        update: () => {},
    });
    expect("input").toHaveValue("Last 7 Days");
});

test("Default date with this_month", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: "this_month",
        update: () => {},
    });
    expect("input").toHaveValue("Current Month");
});

test("Default date with this_quarter", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: "this_quarter",
        update: () => {},
    });
    expect("input").toHaveValue("Current Quarter");
});

test("Default date with this_year", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: "this_year",
        update: () => {},
    });
    expect("input").toHaveValue("Current Year");
});

test("All the options should be displayed", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: undefined,
        update: () => {},
    });
    await contains("input").click();
    const options = fixture.querySelectorAll(".o-dropdown-item");
    expect(options.length).toBe(13);
    expect(options[0].textContent).toBe("Today");
    expect(options[1].textContent).toBe("Yesterday");
    expect(options[2].textContent).toBe("Last 7 Days");
    expect(options[3].textContent).toBe("Last 30 Days");
    expect(options[4].textContent).toBe("Last 90 Days");
    expect(options[5].textContent).toBe("Month to Date");
    expect(options[6].textContent).toBe("Last Month");
    expect(options[7].textContent).toBe("Current Month");
    expect(options[8].textContent).toBe("Current Quarter");
    expect(options[9].textContent).toBe("Year to Date");
    expect(options[10].textContent).toBe("Last 12 Months");
    expect(options[11].textContent).toBe("Current Year");
    expect(options[12].textContent).toBe("All time");
});

test("Can select a relative period", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toBe("last_30_days");
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-dropdown-item[data-id='last_30_days']").click();
    expect.verifySteps(["update"]);
});

test("Can select this month", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toBe("this_month");
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-dropdown-item[data-id='this_month']").click();
    expect.verifySteps(["update"]);
});

test("Can select all time", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: "last_7_days",
        update: (value) => {
            expect(value).toBe(undefined);
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-dropdown-item:not([data-id])").click();
    expect.verifySteps(["update"]);
});

test("Input value is correct for the current value", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: "last_30_days",
        update: () => {},
    });
    expect("input").toHaveValue("Last 30 Days");
    await contains("input").click();
    expect(".selected").toHaveText("Last 30 Days");
});

test("Input value is correct for all time", async function () {
    const env = await makeMockEnv();
    await mountDefaultDateValue(env, {
        value: undefined,
        update: () => {},
    });
    expect("input").toHaveValue("All time");
    await contains("input").click();
    expect(".selected").toHaveText("All time");
});
