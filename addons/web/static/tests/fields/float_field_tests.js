/** @odoo-module **/

import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";
import { click, editInput, getFixture, triggerEvent } from "../helpers/utils";
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
                        float_field: { string: "Float field", type: "float" },
                        int_field: { string: "Int field", type: "integer" },
                    },
                    records: [
                        { id: 1, float_field: 0.36 },
                        { id: 2, float_field: 0 },
                        { id: 3, float_field: -3.89859 },
                        { id: 4, float_field: false },
                        { id: 5, float_field: 9.1 },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("FloatField");

    QUnit.test("unset field should be set to 0", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 4,
            arch: `<form><field name="float_field"/></form>`,
        });

        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "Non-set float field should be considered as 0.00"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "0.00",
            "Non-set float field should be considered as 0."
        );
    });

    QUnit.test("use correct digit precision from field definition", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.float_field.digits = [0, 1];

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field"/></form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_float").textContent,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("use correct digit precision from options", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 1] }" /></form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_float").textContent,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("use correct digit precision from field attrs", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field" digits="[0, 1]" /></form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_float").textContent,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("basic flow in form view", async function (assert) {
        assert.expect(6);

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
            target.querySelector(".o_field_widget").textContent,
            "0.000",
            "The value should be displayed properly."
        );

        await click(target, ".o_form_button_edit");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=float_field] input").value,
            "0.000",
            "The value should be rendered with correct precision."
        );

        target.querySelector(".o_field_widget[name=float_field] input").value = "108.2451938598598";

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=float_field] input").value,
            "108.2451938598598",
            "The value should not be formated yet."
        );

        await triggerEvent(
            target.querySelector(".o_field_widget[name=float_field] input"),
            null,
            "change"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=float_field] input").value,
            "108.245",
            "The value should be formated"
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "18.8958938598598");
        await click(target, ".o_form_button_save");

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "18.896",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("use a formula", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        await click(target, ".o_form_button_edit");
        await editInput(target, ".o_field_widget[name=float_field] input", "=20+3*2");
        await click(target, ".o_form_button_save");

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "26.000",
            "The new value should be calculated properly."
        );

        await click(target, ".o_form_button_edit");
        await editInput(target, ".o_field_widget[name=float_field] input", "=2**3");
        await click(target, ".o_form_button_save");

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "8.000",
            "The new value should be calculated properly."
        );

        await click(target, ".o_form_button_edit");
        await editInput(target, ".o_field_widget[name=float_field] input", "=2^3");
        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "8.000",
            "The new value should be calculated properly."
        );

        await click(target, ".o_form_button_edit");
        await editInput(target, ".o_field_widget[name=float_field] input", "=100/3");
        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "33.333",
            "The new value should be calculated properly."
        );
    });

    QUnit.test("use incorrect formula", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        await click(target, ".o_form_button_edit");
        await editInput(target, ".o_field_widget[name=float_field] input", "=abc");
        await click(target, ".o_form_button_save");

        assert.hasClass(
            target.querySelector(".o_field_widget[name=float_field]"),
            "o_field_invalid",
            "fload field should be displayed as invalid"
        );
        assert.containsOnce(target, ".o_form_editable", "form view should still be editable");

        await editInput(target, ".o_field_widget[name=float_field] input", "=3:2?+4");
        await click(target, ".o_form_button_save");

        assert.containsOnce(target, ".o_form_editable", "form view should still be editable");
        assert.hasClass(
            target.querySelector(".o_field_widget[name=float_field]"),
            "o_field_invalid",
            "float field should be displayed as invalid"
        );
    });

    QUnit.skipWOWL("float field in editable list view", async function (assert) {
        assert.expect(4);

        const list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch:
                '<tree editable="bottom">' +
                '<field name="float_field" widget="float" digits="[5,3]"/>' +
                "</tree>",
        });

        var zeroValues = Array.from(target.querySelectorAll("td.o_field_cell")).filter(
            (el) => el.innerText === ""
        );
        assert.strictEqual(
            zeroValues.length,
            1,
            "Unset float values should be rendered as empty strings."
        );

        // switch to edit mode
        var cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        await click(cell);

        assert.containsOnce(
            list,
            'div[name="float_field"] input',
            "The view should have 1 input for editable float."
        );

        await editInput(target, 'div[name="float_field"] input', "108.2458938598598");
        assert.strictEqual(
            target.querySelector('div[name="float_field"] input').value,
            "108.2458938598598",
            "The value should not be formated yet."
        );

        await editInput(target, 'div[name="float_field"] input', "18.8958938598598");
        await click(target.querySelector(".o_list_button_save"));
        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "18.896",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("do not trigger a field_changed if they have not changed", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].float_field = false;
        serverData.models.partner.records[0].int_field = false;
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="float_field" widget="float" digits="[5,3]"/>' +
                '<field name="int_field"/>' +
                "</sheet>" +
                "</form>",
            mockRPC(route, { method }) {
                assert.step(method);
            },
            resId: 1,
        });

        await click(target.querySelector(".o_form_button_edit"));
        await click(target.querySelector(".o_form_button_save"));

        assert.verifySteps(["read"]); // should not have save as nothing changed
    });

    QUnit.skipWOWL("float widget on monetary field", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.monetary = { string: "Monetary", type: "monetary" };
        serverData.models.partner.records[0].monetary = 9.99;
        serverData.models.partner.records[0].currency_id = 1;

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="monetary" widget="float"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</sheet>" +
                "</form>",
            resId: 1,
            /*
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },*/
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=monetary]").innerText,
            "9.99",
            "value should be correctly formatted (with the float formatter)"
        );
    });

    QUnit.skipWOWL(
        "float field with monetary widget and decimal precision",
        async function (assert) {
            assert.expect(5);

            serverData.models.partner.records = [
                {
                    id: 1,
                    float_field: -8.89859,
                    currency_id: 1,
                },
            ];
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    '<field name="float_field" widget="monetary" options="{\'field_digits\': True}"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                    "</sheet>" +
                    "</form>",
                resId: 1,
                /*
                session: {
                    currencies: _.indexBy(this.data.currency.records, "id"),
                },*/
            });

            // Non-breaking space between the currency and the amount
            assert.strictEqual(
                target.querySelector(".o_field_widget").textContent,
                "$\u00a0-8.9",
                "The value should be displayed properly."
            );

            await click(target.querySelector(".o_form_button_edit"));
            assert.strictEqual(
                target.querySelector(".o_field_widget[name=float_field] input").value,
                "-8.9",
                "The input should be rendered without the currency symbol."
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name=float_field] input").parentElement
                    .firstChild.textContent,
                "$",
                "The input should be preceded by a span containing the currency symbol."
            );

            await editInput(target, ".o_field_monetary input", "109.2458938598598");
            assert.strictEqual(
                target.querySelector(".o_field_widget[name=float_field] input").value,
                "109.2458938598598",
                "The value should not be formated yet."
            );

            await click(target.querySelector(".o_form_button_save"));
            // Non-breaking space between the currency and the amount
            assert.strictEqual(
                target.querySelector(".o_field_widget").textContent,
                "$\u00a0109.2",
                "The new value should be rounded properly."
            );
        }
    );

    QUnit.skipWOWL("float field with type number option", async function (assert) {
        assert.expect(4);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<field name=\"float_field\" options=\"{'type': 'number'}\"/>" +
                "</form>",
            resId: 4,
        });
        registry.category("services").remove("localization");
        registry
            .category("services")
            .add(
                "localization",
                makeFakeLocalizationService({ thousandsSep: ",", grouping: [3, 0] })
            );

        await click(target.querySelector(".o_form_button_edit"));
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
        await click(target.querySelector(".o_form_button_save"));
        await click(target.querySelector(".o_form_button_edit"));
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "123456.789",
            "Float value must be not formatted if input type is number."
        );
        await click(target.querySelector(".o_form_button_save"));
        assert.strictEqual(
            target.querySelector(".o_field_widget").innerText,
            "123,456.8",
            "Float value must be formatted in readonly view even if the input type is number."
        );
    });

    QUnit.skipWOWL(
        "float field with type number option and comma decimal separator",
        async function (assert) {
            assert.expect(4);

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    '<form string="Partners">' +
                    "<field name=\"float_field\" options=\"{'type': 'number'}\"/>" +
                    "</form>",
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

            await click(target.querySelector(".o_form_button_edit"));
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
            await click(target.querySelector(".o_form_button_save"));
            await click(target.querySelector(".o_form_button_edit"));
            assert.strictEqual(
                target.querySelector(".o_field_widget").value,
                "123456.789",
                "Float value must be not formatted if input type is number."
            );
            await click(target.querySelector(".o_form_button_save"));
            assert.strictEqual(
                target.querySelector(".o_field_widget").innerText,
                "123.456,8",
                "Float value must be formatted in readonly view even if the input type is number."
            );
        }
    );

    QUnit.skipWOWL("float field without type number option", async function (assert) {
        assert.expect(2);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form string="Partners">' + '<field name="float_field"/>' + "</form>",
            resId: 4,
        });
        registry.category("services").remove("localization");
        registry
            .category("services")
            .add(
                "localization",
                makeFakeLocalizationService({ thousandsSep: ",", grouping: [3, 0] })
            );

        await click(target.querySelector(".o_form_button_edit"));
        assert.hasAttrValue(
            target.querySelector(".o_field_widget input"),
            "type",
            "text",
            "Float field with option type must have a text type (default type)."
        );

        await editInput(target, ".o_field_widget[name=float_field] input", "123456.7890");
        await click(target.querySelector(".o_form_button_save"));
        await click(target.querySelector(".o_form_button_edit"));
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "123,456.8",
            "Float value must be formatted if input type isn't number."
        );
    });
});
