/** @odoo-module **/

import { click, triggerEvent } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            trim: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                    },
                    records: [
                        {
                            qux: 0.44444,
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

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: ` <form string="Partners">
                        <field name="qux" widget="percentage"/>
                    </form>`,
            mockRPC(route, { args, method }) {
                if (method === "write") {
                    assert.strictEqual(
                        args[1].qux,
                        0.24,
                        "the correct float value should be saved"
                    );
                }
            },
            resId: 1,
        });
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").innerText,
            "44.4%",
            "The value should be displayed properly."
        );
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] input").value,
            "44.444",
            "The input should be rendered without the percentage symbol."
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=qux] span").innerText,
            "%",
            "The input should be followed by a span containing the percentage symbol."
        );
        const field = form.el.querySelector(".o_percentage_field");
        field.value = "24";
        await triggerEvent(field, null, "change");
        assert.strictEqual(field.value, "24", "The value should not be formated yet.");
        await click(form.el.querySelector(".o_form_button_save"));
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").innerText,
            "24%",
            "The new value should be formatted properly."
        );
    });
});
