import { describe, expect, test, getFixture } from "@odoo/hoot";
import { makeMockEnv, contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getTemplate } from "@web/core/templates";
import { BooleanMultiSelector } from "@spreadsheet/global_filters/components/boolean_multi_selector/boolean_multi_selector";

describe.current.tags("desktop");
defineSpreadsheetModels();

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountBooleanMultiSelector(env, props) {
    await mountWithCleanup(BooleanMultiSelector, { props, env, getTemplate });
}

test("basic boolean multi selector", async function () {
    const env = await makeMockEnv();
    await mountBooleanMultiSelector(env, {
        selectedValues: [],
        update: (values) => {
            expect(values).toEqual([true]);
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains("input").click();
    await contains("a:first").click();
    expect.verifySteps(["update"]);
});

test("Autocomplete only provide values that are not selected", async function () {
    const env = await makeMockEnv();
    await mountBooleanMultiSelector(env, {
        selectedValues: [true],
        update: () => {},
    });
    await contains("input").click();
    const options = getFixture().querySelectorAll(".o-autocomplete a");
    expect(options.length).toBe(1);
    expect(options[0].textContent).toBe("Is not set");
});

test("Can click on delete", async function () {
    const env = await makeMockEnv();
    await mountBooleanMultiSelector(env, {
        selectedValues: [true, false],
        update: (values) => {
            expect(values).toEqual([false]);
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    await contains(".o_badge:first .o_delete").click();
    expect.verifySteps(["update"]);
});
