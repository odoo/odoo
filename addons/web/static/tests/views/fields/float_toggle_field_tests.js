/** @odoo-module **/

import { click, clickSave, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        float_field: { string: "Float field", type: "float" },
                    },
                    records: [{ id: 1, float_field: 0.44444 }],
                },
            },
        };
        setupViewRegistries();
        target = getFixture();
    });

    QUnit.module("FloatToggleField");

    QUnit.test("basic flow in form view", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="float_field" widget="float_toggle" options="{'factor': 0.125, 'range': [0, 1, 0.75, 0.5, 0.25]}" digits="[5,3]"/>
                </form>`,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    // 1.000 / 0.125 = 8
                    assert.step(args[1].float_field.toString());
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "0.056", // 0.4444 * 0.125
            "The formatted time value should be displayed properly."
        );
        assert.strictEqual(
            target.querySelector("button.o_field_float_toggle").textContent,
            "0.056",
            "The value should be rendered correctly on the button."
        );

        await click(target.querySelector("button.o_field_float_toggle"));

        assert.strictEqual(
            target.querySelector("button.o_field_float_toggle").textContent,
            "0.000",
            "The value should be rendered correctly on the button."
        );

        // note, 0 will not be written, it's kept in the _changes of the datapoint.
        // because save has not been clicked.

        await click(target.querySelector("button.o_field_float_toggle"));

        assert.strictEqual(
            target.querySelector("button.o_field_float_toggle").textContent,
            "1.000",
            "The value should be rendered correctly on the button."
        );

        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "1.000",
            "The new value should be saved and displayed properly."
        );

        assert.verifySteps(["8"]);
    });

    QUnit.test("kanban view (readonly) with option force_button", async function (assert) {
        await makeView({
            type: "kanban",
            serverData,
            resModel: "partner",
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="float_field" widget="float_toggle" options="{'force_button': true}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsOnce(
            target,
            "button.o_field_float_toggle",
            "should have rendered toggle button"
        );

        const value = target.querySelector("button.o_field_float_toggle").textContent;
        await click(target.querySelector("button.o_field_float_toggle"));
        assert.notEqual(
            target.querySelector("button.o_field_float_toggle").textContent,
            value,
            "float_field field value should be changed"
        );
    });
});
