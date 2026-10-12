import { describe, expect, getFixture, test } from "@odoo/hoot";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { SelectionFilterValue } from "@spreadsheet/global_filters/components/selection_filter_value/selection_filter_value";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSpreadsheetModels();

/**
 * res.currency.position is a selection field with 2 options:
 * - after (A)
 * - before (B)
 */

test("basic selection filter value", async function () {
    await mountWithCleanup(SelectionFilterValue, {
        props: {
            value: [],
            resModel: "res.currency",
            field: "position",
            onValueChanged: (values) => {
                expect(values).toEqual(["after"]);
                expect.step("onValueChanged");
            },
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    const options = getFixture().querySelectorAll(".o-autocomplete a");
    expect(options.length).toBe(2);
    expect(options[0].textContent).toBe("A");
    expect(options[1].textContent).toBe("B");
    await contains("a:first").click();
    expect.verifySteps(["onValueChanged"]);
});

test("Autocomplete only provide values that are not selected", async function () {
    await mountWithCleanup(SelectionFilterValue, {
        props: {
            value: ["after"],
            resModel: "res.currency",
            field: "position",
            onValueChanged: () => {},
        },
    });
    await contains("input").click();
    const options = getFixture().querySelectorAll(".o-autocomplete a");
    expect(options.length).toBe(1);
    expect(options[0].textContent).toBe("B");
});

test("Can click on delete", async function () {
    await mountWithCleanup(SelectionFilterValue, {
        props: {
            value: ["after", "before"],
            resModel: "res.currency",
            field: "position",
            onValueChanged: (values) => {
                expect(values).toEqual(["before"]);
                expect.step("onValueChanged");
            },
        },
    });
    expect.verifySteps([]);
    await contains(".o_badge:first .o_delete").click();
    expect.verifySteps(["onValueChanged"]);
});
