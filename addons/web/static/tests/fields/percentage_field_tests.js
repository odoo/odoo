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
                    fields: {
                        float_field: {
                            string: "Float_field",
                            type: "float",
                            digits: [0, 1],
                        },
                    },
                    records: [
                        {
                            float_field: 0.44444,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("PercentageField");

    QUnit.test("PercentageField in form view", async function (assert) {
        assert.expect(6);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: ` <form>
                        <field name="float_field" widget="percentage"/>
                    </form>`,
            mockRPC(route, { args, method }) {
                if (method === "write") {
                    assert.strictEqual(
                        args[1].float_field,
                        0.24,
                        "the correct float value should be saved"
                    );
                }
            },
            resId: 1,
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "44.4%",
            "The value should be displayed properly."
        );
        await click(target.querySelector(".o_form_button_edit"));
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=float_field] input").value,
            "44.444",
            "The input should be rendered without the percentage symbol."
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=float_field] span").textContent,
            "%",
            "The input should be followed by a span containing the percentage symbol."
        );
        const field = target.querySelector("input");
        await editInput(target, "input", "24");
        assert.strictEqual(field.value, "24", "The value should not be formated yet.");
        await click(target.querySelector(".o_form_button_save"));
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "24%",
            "The new value should be formatted properly."
        );
    });
});
