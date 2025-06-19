import { describe, expect, test } from "@odoo/hoot";
import { makeMockEnv, contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getTemplate } from "@web/core/templates";
import { NumericFilterValue } from "@spreadsheet/global_filters/components/numeric_filter_value/numeric_filter_value";

describe.current.tags("desktop");
defineSpreadsheetModels();

/**
 *
 * @param {{ model: Model, filter: object}} props
 */
async function mountNumericFilterValue(env, props) {
    await mountWithCleanup(NumericFilterValue, { props, env, getTemplate });
}

test("numeric filter with no default value prop", async function () {
    const env = await makeMockEnv();
    await mountNumericFilterValue(env, {
        onValueChanged: (value) => {
            expect(value).toEqual(1998);
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    expect(".o_input").toHaveText("");
    await contains("input").edit(1998);
    await contains("input").press("Enter");
    expect.verifySteps(["update"]);
    expect(".o_input").toHaveValue(1998);
});

test("numeric filter with default value prop", async function () {
    const env = await makeMockEnv();
    await mountNumericFilterValue(env, {
        value: 1999,
        onValueChanged: () => {},
    });
    expect(".o_input").toHaveValue(1999);
});

test("change value of numeric filter with default value prop", async function () {
    const env = await makeMockEnv();
    await mountNumericFilterValue(env, {
        value: 1999,
        onValueChanged: (value) => {
            expect(value).toEqual(2000);
            expect.step("update");
        },
    });
    expect.verifySteps([]);
    expect(".o_input").toHaveValue(1999);
    await contains("input").edit(2000);
    await contains("input").press("Enter");
    expect.verifySteps(["update"]);
    expect(".o_input").toHaveValue(2000);
});
