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
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                    },
                    records: [{ id: 5, qux: 9.1 }],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("FloatTimeField");

    QUnit.test("FloatTimeField in form view", async function (assert) {
        assert.expect(5);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="float_time"/>' +
                "</sheet>" +
                "</form>",
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    // 48 / 60 = 0.8
                    assert.strictEqual(
                        args.args[1].qux,
                        -11.8,
                        "the correct float value should be saved"
                    );
                }
            },
            resId: 5,
        });

        // 9 + 0.1 * 60 = 9.06
        assert.strictEqual(
            target.querySelector(".o_field_widget").innerText,
            "09:06",
            "The formatted time value should be displayed properly."
        );

        await click(target, ".o_form_button_edit");
        assert.strictEqual(
            target.querySelector(".o_field_float_time[name=qux] input").value,
            "09:06",
            "The value should be rendered correctly in the input."
        );

        await editInput(
            target.querySelector(".o_field_float_time[name=qux] input"),
            null,
            "-11:48"
        );
        assert.strictEqual(
            target.querySelector(".o_field_float_time[name=qux] input").value,
            "-11:48",
            "The new value should be displayed properly in the input."
        );

        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_field_widget").innerText,
            "-11:48",
            "The new value should be saved and displayed properly."
        );
    });

    QUnit.test("FloatTimeField value formatted on blur", async function (assert) {
        assert.expect(4);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `<form string="Partners">
                    <field name="qux" widget="float_time"/>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(
                        args.args[1].qux,
                        9.5,
                        "the correct float value should be saved"
                    );
                }
            },
            resId: 5,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").innerText,
            "09:06",
            "The formatted time value should be displayed properly."
        );

        await click(target, ".o_form_button_edit");
        await editInput(target.querySelector(".o_field_float_time[name=qux] input"), null, "9.5");
        assert.strictEqual(
            target.querySelector(".o_field_float_time[name=qux] input").value,
            "09:30",
            "The new value should be displayed properly in the input."
        );

        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_field_widget").innerText,
            "09:30",
            "The new value should be saved and displayed properly."
        );
    });

    QUnit.test("FloatTimeField with invalid value", async function (assert) {
        assert.expect(5);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `<form>
                    <field name="qux" widget="float_time"/>
                </form>`,
        });

        await editInput(
            target.querySelector(".o_field_float_time[name=qux] input"),
            null,
            "blabla"
        );
        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_notification_title").textContent,
            "Invalid fields: "
        );
        assert.strictEqual(
            target.querySelector(".o_notification_content").innerHTML,
            "<ul><li>Qux</li></ul>"
        );
        assert.hasClass(target.querySelector(".o_notification"), "border-danger");
        assert.hasClass(target.querySelector(".o_field_float_time[name=qux]"), "o_field_invalid");

        await editInput(target.querySelector(".o_field_float_time[name=qux] input"), null, "6.5");
        assert.doesNotHaveClass(
            target.querySelector(".o_field_float_time[name=qux] input"),
            "o_field_invalid",
            "date field should not be displayed as invalid now"
        );
    });
});
