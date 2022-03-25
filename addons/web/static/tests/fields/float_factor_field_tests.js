/** @odoo-module **/

import { click, editInput, getFixture } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: { qux: { string: "Qux", type: "float", digits: [16, 1] } },
                    records: [{ id: 1, qux: 9.1 }],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("FloatFactorField");

    QUnit.test("FloatFactorField in form view", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="qux" widget="float_factor" options="{'factor': 0.5}" digits="[16,2]" />
                    </sheet>
                </form>
            `,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    // 2.3 / 0.5 = 4.6
                    assert.strictEqual(args[1].qux, 4.6, "the correct float value should be saved");
                }
            },
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "4.55", // 9.1 / 0.5
            "The formatted value should be displayed properly."
        );

        await click(target, ".o_form_button_edit");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='qux'] input").value,
            "4.55",
            "The value should be rendered correctly in the input."
        );

        await editInput(target, ".o_field_widget[name='qux'] input", "2.3");
        await click(target, ".o_form_button_save");

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "2.30",
            "The new value should be saved and displayed properly."
        );
    });
});
