/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { click, clickSave, editInput, getFixture, triggerEvent } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        float_field: { string: "Float field", type: "float" },
                        int_field: { string: "Int field", type: "integer" },
                    },
                    records: [
                        { id: 1, float_field: 0.36 },
                        { id: 2, float_field: 0 },
                        { id: 3, float_field: -3.89859 },
                        { id: 4, float_field: false },
                        { id: 5, float_field: 9.1 },
                        { id: 100, float_field: 2.034567e3 },
                        { id: 101, float_field: 3.75675456e6 },
                        { id: 102, float_field: 6.67543577586e12 },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("FloatField");

    QUnit.test("human readable format 1", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 101,
            arch: `<form><field name="float_field" options="{'human_readable': 'true'}"/></form>`,
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "4M",
            "The value should be rendered in human readable format (k, M, G, T)."
        );
    });

    QUnit.test("human readable format 2", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 100,
            arch: `<form><field name="float_field" options="{'human_readable': 'true', 'decimals': 1}"/></form>`,
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "2.0k",
            "The value should be rendered in human readable format (k, M, G, T)."
        );
    });

    QUnit.test("human readable format 3", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 102,
            arch: `<form><field name="float_field" options="{'human_readable': 'true', 'decimals': 4}"/></form>`,
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "6.6754T",
            "The value should be rendered in human readable format (k, M, G, T)."
        );
    });

    QUnit.test("still human readable when readonly", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 102,
            arch: `<form><field readonly="true" name="float_field" options="{'human_readable': 'true', 'decimals': 4}"/></form>`,
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget span").textContent,
            "6.6754T",
            "The value should be rendered in human readable format when input is readonly."
        );
    });

    QUnit.test("unset field should be set to 0", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 4,
            arch: '<form><field name="float_field"/></form>',
        });

        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "Non-set float field should be considered as 0.00"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "0.00",
            "Non-set float field should be considered as 0."
        );
    });

    QUnit.test("use correct digit precision from field definition", async function (assert) {
        serverData.models.partner.fields.float_field.digits = [0, 1];

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="float_field"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_float input").value,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("use correct digit precision from options", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 1] }" /></form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_float input").value,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("use correct digit precision from field attrs", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="float_field" digits="[0, 1]" /></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_float input").value,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("with 'step' option", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field" options="{'type': 'number', 'step': 0.3}"/></form>`,
        });

        assert.ok(
            target.querySelector(".o_field_widget input").hasAttribute("step"),
            "Integer field with option type must have a step attribute."
        );

        assert.hasAttrValue(
            target.querySelector(".o_field_widget input"),
            "step",
            "0.3",
            'Integer field with option type must have a step attribute equals to "3".'
        );
    });

    QUnit.test("basic flow in form view", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "Float field should be considered set for value 0."
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "0.000",
            "The value should be displayed properly."
        );

        await editInput(target, 'div[name="float_field"] input', "108.2451938598598");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=float_field] input").value,
            "108.245",
            "The value should have been formatted on blur."
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "18.8958938598598");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "18.896",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("use a formula", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        await editInput(target, ".o_field_widget[name=float_field] input", "=20+3*2");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "26.000",
            "The new value should be calculated properly."
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "=2**3");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "8.000",
            "The new value should be calculated properly."
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "=2^3");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "8.000",
            "The new value should be calculated properly."
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "=100/3");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "33.333",
            "The new value should be calculated properly."
        );
    });

    QUnit.test("use incorrect formula", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        await editInput(target, ".o_field_widget[name=float_field] input", "=abc");
        await clickSave(target);

        assert.hasClass(
            target.querySelector(".o_field_widget[name=float_field]"),
            "o_field_invalid",
            "fload field should be displayed as invalid"
        );
        assert.containsOnce(target, ".o_form_editable", "form view should still be editable");

        await editInput(target, ".o_field_widget[name=float_field] input", "=3:2?+4");
        await clickSave(target);

        assert.containsOnce(target, ".o_form_editable", "form view should still be editable");
        assert.hasClass(
            target.querySelector(".o_field_widget[name=float_field]"),
            "o_field_invalid",
            "float field should be displayed as invalid"
        );
    });

    QUnit.test("float field in editable list view", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree editable="bottom">
                    <field name="float_field" widget="float" digits="[5,3]" />
                </tree>`,
        });

        // switch to edit mode
        await click(target.querySelector("tr.o_data_row td:not(.o_list_record_selector)"));

        assert.containsOnce(
            target,
            'div[name="float_field"] input',
            "The view should have 1 input for editable float."
        );

        await editInput(target, 'div[name="float_field"] input', "108.2458938598598");
        assert.strictEqual(
            target.querySelector('div[name="float_field"] input').value,
            "108.246",
            "The value should have been formatted on blur."
        );

        await editInput(target, 'div[name="float_field"] input', "18.8958938598598");
        await click(
            target.querySelector(
                ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_save"
            )
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "18.896",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("float field with type number option", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="float_field" options="{'type': 'number'}"/>
                </form>`,
            resId: 4,
        });
        registry.category("services").remove("localization");
        registry
            .category("services")
            .add(
                "localization",
                makeFakeLocalizationService({ thousandsSep: ",", grouping: [3, 0] })
            );

        assert.ok(
            target.querySelector(".o_field_widget input").hasAttribute("type"),
            "Float field with option type must have a type attribute."
        );
        assert.hasAttrValue(
            target.querySelector(".o_field_widget input"),
            "type",
            "number",
            'Float field with option type must have a type attribute equals to "number".'
        );
        await editInput(target, ".o_field_widget[name=float_field] input", "123456.7890");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "123456.789",
            "Float value must be not formatted if input type is number. (but the trailing 0 is gone)"
        );
    });

    QUnit.test(
        "float field with type number option and comma decimal separator",
        async function (assert) {
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <field name="float_field" options="{'type': 'number'}"/>
                    </form>`,
                resId: 4,
            });
            registry.category("services").remove("localization");
            registry.category("services").add(
                "localization",
                makeFakeLocalizationService({
                    thousandsSep: ".",
                    decimalPoint: ",",
                    grouping: [3, 0],
                })
            );

            assert.ok(
                target.querySelector(".o_field_widget input").hasAttribute("type"),
                "Float field with option type must have a type attribute."
            );
            assert.hasAttrValue(
                target.querySelector(".o_field_widget input"),
                "type",
                "number",
                'Float field with option type must have a type attribute equals to "number".'
            );
            await editInput(target, ".o_field_widget[name=float_field] input", "123456.789");
            await clickSave(target);
            assert.strictEqual(
                target.querySelector(".o_field_widget input").value,
                "123456.789",
                "Float value must be not formatted if input type is number."
            );
        }
    );

    QUnit.test("float field without type number option", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="float_field"/></form>',
            resId: 4,
        });
        registry.category("services").remove("localization");
        registry
            .category("services")
            .add(
                "localization",
                makeFakeLocalizationService({ thousandsSep: ",", grouping: [3, 0] })
            );

        assert.hasAttrValue(
            target.querySelector(".o_field_widget input"),
            "type",
            "text",
            "Float field with option type must have a text type (default type)."
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "123456.7890");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "123,456.79",
            "Float value must be formatted if input type isn't number."
        );
    });

    QUnit.test("field with enable_formatting option as false", async function (assert) {
        registry.category("services").remove("localization");
        registry
            .category("services")
            .add(
                "localization",
                makeFakeLocalizationService({ thousandsSep: ",", grouping: [3, 0] })
            );

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field" options="{'enable_formatting': false}"/></form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "0.36",
            "Integer value must not be formatted"
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "123456.789");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "123456.789",
            "Integer value must be not formatted if input type is number."
        );
    });

    QUnit.test(
        "field with enable_formatting option as false in editable list view",
        async function (assert) {
            await makeView({
                serverData,
                type: "list",
                resModel: "partner",
                arch: `
                <tree editable="bottom">
                    <field name="float_field" widget="float" digits="[5,3]" options="{'enable_formatting': false}" />
                </tree>`,
            });

            // switch to edit mode
            await click(target.querySelector("tr.o_data_row td:not(.o_list_record_selector)"));

            assert.containsOnce(
                target,
                'div[name="float_field"] input',
                "The view should have 1 input for editable float."
            );

            await editInput(target, 'div[name="float_field"] input', "108.2458938598598");
            assert.strictEqual(
                target.querySelector('div[name="float_field"] input').value,
                "108.2458938598598",
                "The value should not be formatted on blur."
            );

            await editInput(target, 'div[name="float_field"] input', "18.8958938598598");
            await click(
                target.querySelector(
                    ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_save"
                )
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget").textContent,
                "18.8958938598598",
                "The new value should not be rounded as well."
            );
        }
    );

    QUnit.test("float_field field with placeholder", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="float_field" placeholder="Placeholder"/></form>',
        });

        const input = target.querySelector(".o_field_widget[name='float_field'] input");
        input.value = "";
        await triggerEvent(input, null, "input");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='float_field'] input").placeholder,
            "Placeholder"
        );
    });

    QUnit.test("float field can be updated by another field/widget", async function (assert) {
        class MyWidget extends Component {
            static template = xml`<button t-on-click="onClick">do it</button>`;
            onClick() {
                const val = this.props.record.data.float_field;
                this.props.record.update({ float_field: val + 1 });
            }
        }
        const myWidget = {
            component: MyWidget,
        };
        registry.category("view_widgets").add("wi", myWidget);
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="float_field"/>
                    <field name="float_field"/>
                    <widget name="wi"/>
                </form>`,
        });

        await editInput(
            target.querySelector(".o_field_widget[name=float_field] input"),
            null,
            "40"
        );

        assert.strictEqual(
            "40.00",
            target.querySelectorAll(".o_field_widget[name=float_field] input")[0].value
        );
        assert.strictEqual(
            "40.00",
            target.querySelectorAll(".o_field_widget[name=float_field] input")[1].value
        );

        await click(target, ".o_widget button");

        assert.strictEqual(
            "41.00",
            target.querySelectorAll(".o_field_widget[name=float_field] input")[0].value
        );
        assert.strictEqual(
            "41.00",
            target.querySelectorAll(".o_field_widget[name=float_field] input")[1].value
        );
    });

    QUnit.test("float field with digits=0", async function (assert) {
        // This isn't in the orm documentation, so it shouldn't be supported, but
        // people do it and thus now we need to support it.
        // Historically, it behaves like "no digits attribute defined", so it
        // fallbacks on a precision of 2 digits.
        // We will change that in master s.t. we do not round anymore in that case.
        serverData.models.partner.fields.float_field.digits = 0;

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="float_field"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_float input").value,
            "0.36",
            "should contain a number rounded to 1 decimal"
        );
    });
});
