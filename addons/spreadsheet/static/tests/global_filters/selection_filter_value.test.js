import { describe, expect, test, getFixture } from "@odoo/hoot";
import { makeMockEnv, contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getTemplate } from "@web/core/templates";
import { SelectionFilterValue } from "@spreadsheet/global_filters/components/selection_filter_value/selection_filter_value";

describe.current.tags("desktop");
defineSpreadsheetModels();

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountSelectionFilterValue(env, props) {
    await mountWithCleanup(SelectionFilterValue, { props, env, getTemplate });
}

/**
 * res.currency.position is a selection field with 2 options:
 * - after (A)
 * - before (B)
 */

test("basic selection filter value", async function () {
    const env = await makeMockEnv();
    await mountSelectionFilterValue(env, {
        value: [],
        resModel: "res.currency",
        field: "position",
        onValueChanged: (values) => {
            expect(values).toEqual(["after"]);
            expect.step("onValueChanged");
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
    const env = await makeMockEnv();
    await mountSelectionFilterValue(env, {
        value: ["after"],
        resModel: "res.currency",
        field: "position",
        onValueChanged: () => {},
    });
    await contains("input").click();
    const options = getFixture().querySelectorAll(".o-autocomplete a");
    expect(options.length).toBe(1);
    expect(options[0].textContent).toBe("B");
});

test("Can click on delete", async function () {
    const env = await makeMockEnv();
    await mountSelectionFilterValue(env, {
        value: ["after", "before"],
        resModel: "res.currency",
        field: "position",
        onValueChanged: (values) => {
            expect(values).toEqual(["before"]);
            expect.step("onValueChanged");
        },
    });
    expect.verifySteps([]);
    await contains(".o_badge:first .o_delete").click();
    expect.verifySteps(["onValueChanged"]);
});
