import { describe, expect, test, getFixture, beforeEach } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { makeMockEnv, contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { DateFilterValue } from "@spreadsheet/global_filters/components/date_filter_value/date_filter_value";

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
async function mountDateFilterValue(env, props) {
    await mountWithCleanup(DateFilterValue, { props, env });
}

test("basic date filter value", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: () => {
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown:first").click();
    expect.verifySteps(["update"]);
});

test("Date filter without initial value", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: () => {},
    });
    expect("input").toHaveValue("All time");
});

test("Date filter with relative value", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "relative", period: "last_7_days" },
        update: () => {},
    });
    expect("input").toHaveValue("Last 7 Days");
});

test("Date filter with month value", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "month", month: 1, year: 2023 },
        update: () => {},
    });
    expect("input").toHaveValue("January 2023");
});

test("Date filter with quarter value", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "quarter", quarter: 1, year: 2023 },
        update: () => {},
    });
    expect("input").toHaveValue("Q1 2023");
});

test("Date filter with year value", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "year", year: 2023 },
        update: () => {},
    });
    expect("input").toHaveValue("2023");
});

test("Date filter with range value", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "range", from: "2023-01-01", to: "2023-01-31" },
        update: () => {},
    });
    expect("input").toHaveValue("January 1 – 31, 2023");
});

test("Date options are computed from the current date", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: () => {},
    });
    await contains("input").click();
    const inputs = fixture.querySelectorAll(".o-date-filter-dropdown input");
    expect(inputs.length).toBe(5);
    expect(inputs[0].value).toBe("July 2022");
    expect(inputs[1].value).toBe("Q3 2022");
    expect(inputs[2].value).toBe("2022");
    expect(inputs[3].value).toBe("07/01/2022");
    expect(inputs[4].value).toBe("07/31/2022");
});

test("Month props value should override date options", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "month", month: 1, year: 2025 },
        update: () => {},
    });
    await contains("input").click();
    const inputs = fixture.querySelectorAll(".o-date-filter-dropdown input");
    expect(inputs.length).toBe(5);
    expect(inputs[0].value).toBe("January 2025");
    expect(inputs[1].value).toBe("Q3 2022");
    expect(inputs[2].value).toBe("2022");
    expect(inputs[3].value).toBe("01/01/2025");
    expect(inputs[4].value).toBe("01/31/2025");
});

test("Quarter props value should override date options", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "quarter", quarter: 1, year: 2025 },
        update: () => {},
    });
    await contains("input").click();
    const inputs = fixture.querySelectorAll(".o-date-filter-dropdown input");
    expect(inputs.length).toBe(5);
    expect(inputs[0].value).toBe("July 2022");
    expect(inputs[1].value).toBe("Q1 2025");
    expect(inputs[2].value).toBe("2022");
    expect(inputs[3].value).toBe("01/01/2025");
    expect(inputs[4].value).toBe("03/31/2025");
});

test("Year props value should override date options", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "year", year: 2025 },
        update: () => {},
    });
    await contains("input").click();
    const inputs = fixture.querySelectorAll(".o-date-filter-dropdown input");
    expect(inputs.length).toBe(5);
    expect(inputs[0].value).toBe("July 2022");
    expect(inputs[1].value).toBe("Q3 2022");
    expect(inputs[2].value).toBe("2025");
    expect(inputs[3].value).toBe("01/01/2025");
    expect(inputs[4].value).toBe("12/31/2025");
});

test("All the options should be displayed", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: () => {},
    });
    await contains("input").click();
    const options = fixture.querySelectorAll(".o-date-filter-dropdown .o-date-option-label");
    expect(options.length).toBe(14);
    expect(options[0].textContent).toBe("Today");
    expect(options[1].textContent).toBe("Yesterday");
    expect(options[2].textContent).toBe("Last 7 Days");
    expect(options[3].textContent).toBe("Last 30 Days");
    expect(options[4].textContent).toBe("Last 90 Days");
    expect(options[5].textContent).toBe("Month to Date");
    expect(options[6].textContent).toBe("Last Month");
    expect(options[7].textContent).toBe("Month");
    expect(options[8].textContent).toBe("Quarter");
    expect(options[9].textContent).toBe("Year to Date");
    expect(options[10].textContent).toBe("Last 12 Months");
    expect(options[11].textContent).toBe("Year");
    expect(options[12].textContent).toBe("All time");
    expect(options[13].textContent).toBe("Custom Range");
});

test("Opening the custom range calendar does not trigger update", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "range", from: "2023-01-01", to: "2023-01-31" },
        update: () => {
            expect.step("update");
        },
    });

    expect.verifySteps([]);
    await contains("input").click();
    expect.verifySteps([]);
    await contains("input.o_datetime_input:first").click();
    expect(".o_datetime_picker").toHaveCount(1);
    expect.verifySteps([]);
});

test("Can select a relative period", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "relative", period: "last_30_days" });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='last_30_days']").click();
    expect.verifySteps(["update"]);
});

test("Can select a month", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "month", month: 7, year: 2022 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='month']").click();
    expect.verifySteps(["update"]);
});

test("Can select previous month", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "month", month: 6, year: 2022 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='month'] .btn-previous").click();
    expect.verifySteps(["update"]);
});

test("Can select next month", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "month", month: 8, year: 2022 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='month'] .btn-next").click();
    expect.verifySteps(["update"]);
});

test("Can select a quarter", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "quarter", quarter: 3, year: 2022 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='quarter']").click();
    expect.verifySteps(["update"]);
});

test("Can select previous quarter", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "quarter", quarter: 2, year: 2022 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='quarter'] .btn-previous").click();
    expect.verifySteps(["update"]);
});

test("Can select next quarter", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "quarter", quarter: 4, year: 2022 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='quarter'] .btn-next").click();
    expect.verifySteps(["update"]);
});

test("Can select a year", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "year", year: 2022 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='year']").click();
    expect.verifySteps(["update"]);
});

test("Can select previous year", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "year", year: 2021 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='year'] .btn-previous").click();
    expect.verifySteps(["update"]);
});

test("Can select next year", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: (value) => {
            expect(value).toEqual({ type: "year", year: 2023 });
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown[data-id='year'] .btn-next").click();
    expect.verifySteps(["update"]);
});

test("Can select all time", async function () {
    mockDate("2022-07-14 00:00:00");
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "relative", period: "last_7_days" },
        update: (value) => {
            expect(value).toBe(undefined);
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains(".o-date-filter-dropdown:not([data-id])").click();
    expect.verifySteps(["update"]);
});

test("Input value is correct for relative period", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "relative", period: "last_30_days" },
        update: () => {},
    });
    expect("input").toHaveValue("Last 30 Days");
    await contains("input").click();
    expect("div.selected .o-date-option-label").toHaveText("Last 30 Days");
});

test("Input value is correct for month", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "month", month: 1, year: 2023 },
        update: () => {},
    });
    expect("input").toHaveValue("January 2023");
    await contains("input").click();
    expect("div.selected .o-date-option-label").toHaveText("Month");
});

test("Input value is correct for quarter", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "quarter", quarter: 1, year: 2023 },
        update: () => {},
    });
    expect("input").toHaveValue("Q1 2023");
    await contains("input").click();
    expect("div.selected .o-date-option-label").toHaveText("Quarter");
});

test("Input value is correct for year", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "year", year: 2023 },
        update: () => {},
    });
    expect("input").toHaveValue("2023");
    await contains("input").click();
    expect("div.selected .o-date-option-label").toHaveText("Year");
});

test("Input value is correct for range", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "range", from: "2023-01-01", to: "2023-01-31" },
        update: () => {},
    });
    expect("input").toHaveValue("January 1 – 31, 2023");
    await contains("input").click();
    expect("div.selected .o-date-option-label").toHaveText("Custom Range");
});

test("Input value is correct for all time", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: undefined,
        update: () => {},
    });
    expect("input").toHaveValue("All time");
    await contains("input").click();
    expect("div.selected .o-date-option-label").toHaveText("All time");
});

test("Can open date time picker to select a range", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "range", from: "2023-01-01", to: "2023-01-31" },
        update: () => {},
    });
    await contains("input").click();
    expect(".o_datetime_picker").toHaveCount(0);
    await contains("input.o_datetime_input:first").click();
    expect(".o_datetime_picker").toHaveCount(1);
});

test("Choosing a from after the to will re-order dates", async function () {
    const env = await makeMockEnv();
    await mountDateFilterValue(env, {
        value: { type: "range", from: "2023-01-30", to: "2023-01-31" },
        update: (value) => {
            expect(value).toEqual({ type: "range", from: "2023-01-01", to: "2023-01-30" });
            expect.step("update");
        },
    });
    await contains("input").click();
    await contains("input.o_datetime_input:last").click();
    // Select 1st of January 2023
    await contains(".o_date_item_cell.o_datetime_button:first").click();
    expect.verifySteps(["update"]);
});
