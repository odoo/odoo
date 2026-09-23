// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame, check, uncheck } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    defineParams,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { CheckBox } from "@web/components/checkbox/checkbox";

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
    expect(`.form-check`).toHaveText("rugubudubudubu");
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
            this.state = useState({ value: false });
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
            this.state = useState({ value: false });
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

test.tags("desktop");
test("pressing ENTER on a disabled checkbox does nothing", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox disabled="true" onChange.bind="this.onChange" value="this.state.value" />`;

        setup() {
            this.state = useState({ value: false });
        }

        onChange(checked) {
            this.state.value = checked;
            expect.step("changed");
        }
    }

    await mountWithCleanup(Parent);

    expect(`.o-checkbox input`).not.toBeEnabled();
    expect(`.o-checkbox input`).not.toBeChecked();

    await contains(".o-checkbox input").press("Enter");

    expect(`.o-checkbox input`).not.toBeChecked();
    expect.verifySteps([]);
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

test("controlled checkbox is restored when the parent rejects the change", async () => {
    /** @type {boolean} */
    let received;
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox value="this.state.value" onChange.bind="this.onChange"/>`;
        setup() {
            this.state = useState({ value: false });
        }
        onChange(checked) {
            received = checked;
        }
    }
    await mountWithCleanup(Parent);

    await check("input");
    await animationFrame();

    expect(received).toBe(true);
    expect(`.o-checkbox input`).not.toBeChecked();
});

test("uncontrolled checkbox (no value prop) still toggles freely", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox onChange="() => {}"/>`;
    }
    await mountWithCleanup(Parent);

    await check("input");
    expect(`.o-checkbox input`).toBeChecked();

    await uncheck("input");
    expect(`.o-checkbox input`).not.toBeChecked();
});
