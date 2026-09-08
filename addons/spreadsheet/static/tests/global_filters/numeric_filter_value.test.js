import { describe, expect, test } from "@odoo/hoot";
import { keyDown, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { NumericFilterValue } from "@spreadsheet/global_filters/components/numeric_filter_value/numeric_filter_value";
import {
    contains,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { getTemplate } from "@web/core/templates";

describe.current.tags("desktop");
defineSpreadsheetModels();

async function mountNumericFilterValue(env, props) {
    return mountWithCleanup(NumericFilterValue, { props, env, getTemplate });
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

test("clearing numeric filter input should not reset its value to 0", async function () {
    const env = await makeMockEnv();
    await mountNumericFilterValue(env, {
        value: 1998,
        onValueChanged: (value) => {
            expect(value).toEqual(undefined);
            expect.step("reset");
        },
    });
    await contains("input").edit("");
    await contains("input").press("Enter");
    expect.verifySteps(["reset"]);
    expect(".o_input").toHaveValue("");
});

test("setting a string value to numeric filter input should reset its value to 0", async function () {
    const env = await makeMockEnv();
    await mountNumericFilterValue(env, {
        value: undefined,
        onValueChanged: (value) => {
            expect(value).toEqual(0);
            expect.step("reset");
        },
    });
    await contains("input").edit("hola");
    await contains("input").press("Enter");
    expect.verifySteps(["reset"]);
    expect(".o_input").toHaveValue(0);
});

test("numeric filter input value is correctly parsed based on localization", async function () {
    const env = await makeMockEnv();
    patchWithCleanup(localization, {
        decimalPoint: ",",
        thousandsSep: ".",
    });
    await mountNumericFilterValue(env, {
        onValueChanged: (value) => {
            expect(value).toEqual(40048789.87);
            expect.step("parsed");
        },
    });
    await contains("input").edit("40.048.789,87");
    await contains("input").press("Enter");
    expect.verifySteps(["parsed"]);
});

test("numeric filter input should insert localized decimal separator when numpad decimal key is pressed", async function () {
    const env = await makeMockEnv();
    patchWithCleanup(localization, {
        decimalPoint: ",",
        thousandsSep: ".",
    });
    await mountNumericFilterValue(env, {
        onValueChanged: (value) => {
            expect(value).toEqual(0.12);
            expect.step("parsed");
        },
    });
    await contains("input").focus();
    await keyDown(".", { code: "NumpadDecimal" });
    await keyDown("1", { code: "Digit1" });
    await keyDown("2", { code: "Digit2" });
    expect(".o_input").toHaveValue(",12");
    const input = document.querySelector(".o_input");
    input.dispatchEvent(new Event("change"));
    expect.verifySteps(["parsed"]);
});

test("default value is saved after saving and editing again", async function () {
    const env = await makeMockEnv();
    await mountNumericFilterValue(env, {
        value: 2001,
        onValueChanged: () => {},
    });
    expect(".o_input").toHaveValue(2001);
    await mountNumericFilterValue(env, {
        onValueChanged: () => {},
    });
    expect(".o_input").toHaveText("");
});

test("default value does not disappear when pressing enter", async function () {
    let savedValue = null;
    const env = await makeMockEnv();
    await mountNumericFilterValue(env, {
        onValueChanged: (value) => {
            savedValue = value;
        },
    });
    await contains("input").edit("2024");
    await contains("input").press("Enter");
    expect(savedValue).toEqual(2024);

    expect(".o_input").toHaveValue(2024);
});

test("what the user is typing survives a re-render", async function () {
    const env = await makeMockEnv();
    const component = await mountNumericFilterValue(env, {
        value: 1999,
        onValueChanged: () => {},
    });
    // The user is typing: the input is dirty but the prop still holds the
    // saved value, because no change event fired yet.
    await contains("input").focus();
    queryOne("input").value = "42";
    // Anything at all can re-render us here -- the filter list refreshing, a
    // message from the session. It must not throw the typing away.
    component.render();
    await animationFrame();
    expect(queryOne("input").value).toBe("42");
});

test("the input follows the prop when it changes and the input is not focused", async function () {
    class Parent extends Component {
        static components = { NumericFilterValue };
        static props = {};
        static template = xml`
            <NumericFilterValue value="state.value" onValueChanged="() => {}"/>`;
        setup() {
            this.state = useState({ value: 1999 });
        }
    }
    const env = await makeMockEnv();
    const parent = await mountWithCleanup(Parent, { env, getTemplate });
    expect(queryOne("input").value).toBe("1999");
    parent.state.value = 2000;
    await animationFrame();
    expect(queryOne("input").value).toBe("2000");
});
