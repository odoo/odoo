import { expect, test } from "@odoo/hoot";
import { check, uncheck } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
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
        static template = xml`<CheckBox>ragabadabadaba</CheckBox>`;
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
        static template = xml`<CheckBox onChange="onChange" />`;
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

test.tags("desktop")("can toggle value by pressing ENTER", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox onChange.bind="onChange" value="state.value" />`;

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

test.tags("desktop")("toggling through multiple ways", async () => {
    class Parent extends Component {
        static components = { CheckBox };
        static props = {};
        static template = xml`<CheckBox onChange.bind="onChange" value="state.value" />`;

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
