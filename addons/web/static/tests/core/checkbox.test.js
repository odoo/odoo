import { expect, test } from "@odoo/hoot";
import { check, queryFirst, uncheck } from "@odoo/hoot-dom";
import { Component, xml, proxy } from "@odoo/owl";
import { contains, defineParams, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { CheckBox } from "@web/core/checkbox/checkbox";

test("can be rendered", async () => {
    await mountWithCleanup(CheckBox);

    expect(`.o-checkbox input[type=checkbox]`).toHaveCount(1);
    expect(`.o-checkbox input[type=checkbox]`).toBeEnabled();
});

test("has a slot for translatable text", async () => {
    defineParams({ translations: { ragabadabadaba: "rugubudubudubu" } });

    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<div t-translation-context="web"><CheckBox>ragabadabadaba</CheckBox></div>`;
    }

    await mountWithCleanup(Parent);

    expect(`.form-check`).toHaveCount(1);
    expect(`.form-check`).toHaveText("rugubudubudubu", { exact: true });
});

test("call onChange prop when some change occurs", async () => {
    let value = false;
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox onChange="this.onChange" />`;
        onChange(checked) {
            value = checked;
        }
    }

    await mountWithCleanup(Parent);

    expect(`.o-checkbox input`).toHaveCount(1);

    await check("input");

    expect(value).toBe(true);

    await uncheck("input");

    expect(value).toBe(false);
});

test("checkbox with props disabled", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox disabled="true" />`;
    }

    await mountWithCleanup(Parent);

    expect(`.o-checkbox input`).toHaveCount(1);
    expect(`.o-checkbox input`).not.toBeEnabled();
});

test.tags("desktop");
test("can toggle value by pressing ENTER", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox onChange.bind="this.onChange" value="this.state.value" />`;

        setup() {
            this.state = proxy({ value: false });
        }

        onChange(checked) {
            this.state.value = checked;
        }
    }

    await mountWithCleanup(Parent);

    expect(`.o-checkbox input`).toHaveCount(1);
    expect(`.o-checkbox input`).not.toBeChecked();

    await contains(".o-checkbox input").press("Enter");

    expect(`.o-checkbox input`).toBeChecked();

    await contains(".o-checkbox input").press("Enter");

    expect(`.o-checkbox input`).not.toBeChecked();
});

test.tags("desktop");
test("toggling through multiple ways", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox onChange.bind="this.onChange" value="this.state.value" />`;

        setup() {
            this.state = proxy({ value: false });
        }

        onChange(checked) {
            this.state.value = checked;
            expect.step(String(checked));
        }
    }

    await mountWithCleanup(Parent);

    expect(`.o-checkbox input`).toHaveCount(1);
    expect(`.o-checkbox input`).not.toBeChecked();

    await contains(".o-checkbox").click();

    expect(`.o-checkbox input`).toBeChecked();

    await contains(".o-checkbox > .form-check-label", { visible: false }).uncheck();

    expect(`.o-checkbox input`).not.toBeChecked();

    await contains(".o-checkbox input").press("Enter");

    expect(`.o-checkbox input`).toBeChecked();

    await contains(".o-checkbox input").press(" ");

    expect(`.o-checkbox input`).not.toBeChecked();
    expect.verifySteps(["true", "false", "true", "false"]);
});

test("checkbox with props indeterminate", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox indeterminate="true" />`;
    }

    await mountWithCleanup(Parent);

    expect(`.o-checkbox input`).toHaveCount(1);
    expect(`.o-checkbox input`).toBeChecked({ indeterminate: true });
});

test("indeterminate style attribute renders a visible dash", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`
            <CheckBox indeterminate="true" className="'cb-indeterminate'" />
            <CheckBox value="true" className="'cb-checked'" />
            <input type="checkbox" t-att-indeterminate="true" class="form-check-input cb-raw-indeterminate"/>
            <input type="checkbox" checked="1" class="form-check-input cb-raw-checked"/>
        `;
    }

    await mountWithCleanup(Parent);

    const indeterminate = queryFirst(".cb-indeterminate input");
    const checked = queryFirst(".cb-checked input");
    const rawIndeterminate = queryFirst(".cb-raw-indeterminate");
    const rawChecked = queryFirst(".cb-raw-checked");

    const getStrokeColor = (el) =>
        getComputedStyle(el)
            .getPropertyValue("--form-check-bg-image")
            .match(/stroke='(%23[^']+)'/)?.[1];

    // --- CheckBox component ---
    expect(indeterminate).toBeChecked({ indeterminate: true });
    expect(indeterminate.indeterminate).toBe(true);

    expect(getComputedStyle(indeterminate).backgroundColor).toBe(
        getComputedStyle(checked).backgroundColor
    );
    expect(getStrokeColor(indeterminate)).toBe(getStrokeColor(checked));

    // --- Input element ---
    expect(rawIndeterminate.indeterminate).toBe(true);
    expect(rawIndeterminate.checked).toBe(false);
    // Check again color of input match when indeterminate and checked
    expect(getComputedStyle(rawIndeterminate).backgroundColor).toBe(
        getComputedStyle(rawChecked).backgroundColor
    );
    expect(getStrokeColor(rawIndeterminate)).toBe(getStrokeColor(rawChecked));
});
