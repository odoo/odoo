/** @odoo-module **/

import { click, editInput, triggerEvent } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        float_field: { string: "Float field", type: "float" },
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

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 4,
            arch: `<form><field name="float_field"/></form>`,
        });

        assert.doesNotHaveClass(
            form.el.querySelector(".o_field_widget"),
            "o_field_empty",
            "Non-set float field should be considered as 0.00"
        );

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "0.00",
            "Non-set float field should be considered as 0."
        );
    });

    QUnit.test("use correct digit precision from field definition", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.float_field.digits = [0, 1];

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field"/></form>`,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_float").textContent,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("use correct digit precision from options", async function (assert) {
        assert.expect(1);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 1] }" /></form>`,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_float").textContent,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("use correct digit precision from field attrs", async function (assert) {
        assert.expect(1);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="float_field" digits="[0, 1]" /></form>`,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_float").textContent,
            "0.4",
            "should contain a number rounded to 1 decimal"
        );
    });

    QUnit.test("basic flow in form view", async function (assert) {
        assert.expect(6);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        assert.doesNotHaveClass(
            form.el.querySelector(".o_field_widget"),
            "o_field_empty",
            "Float field should be considered set for value 0."
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "0.000",
            "The value should be displayed properly."
        );

        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=float_field] input").value,
            "0.000",
            "The value should be rendered with correct precision."
        );

        form.el.querySelector(".o_field_widget[name=float_field] input").value =
            "108.2451938598598";

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=float_field] input").value,
            "108.2451938598598",
            "The value should not be formated yet."
        );

        await triggerEvent(
            form.el.querySelector(".o_field_widget[name=float_field] input"),
            null,
            "change"
        );

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=float_field] input").value,
            "108.245",
            "The value should be formated"
        );

        await editInput(form.el, ".o_field_widget[name=float_field] input", "18.8958938598598");
        await click(form.el, ".o_form_button_save");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "18.896",
            "The new value should be rounded properly."
        );
    });

    QUnit.test("use a formula", async function (assert) {
        assert.expect(4);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        await click(form.el, ".o_form_button_edit");
        await editInput(form.el, ".o_field_widget[name=float_field] input", "=20+3*2");
        await click(form.el, ".o_form_button_save");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "26.000",
            "The new value should be calculated properly."
        );

        await click(form.el, ".o_form_button_edit");
        await editInput(form.el, ".o_field_widget[name=float_field] input", "=2**3");
        await click(form.el, ".o_form_button_save");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "8.000",
            "The new value should be calculated properly."
        );

        await click(form.el, ".o_form_button_edit");
        await editInput(form.el, ".o_field_widget[name=float_field] input", "=2^3");
        await click(form.el, ".o_form_button_save");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "8.000",
            "The new value should be calculated properly."
        );

        await click(form.el, ".o_form_button_edit");
        await editInput(form.el, ".o_field_widget[name=float_field] input", "=100/3");
        await click(form.el, ".o_form_button_save");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "33.333",
            "The new value should be calculated properly."
        );
    });

    QUnit.skipWOWL("use incorrect formula", async function (assert) {
        assert.expect(4);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `<form><field name="float_field" options="{ 'digits': [0, 3] }" /></form>`,
        });

        await click(form.el, ".o_form_button_edit");
        await editInput(form.el, ".o_field_widget[name=float_field] input", "=abc");
        await click(form.el, ".o_form_button_save");

        assert.hasClass(
            form.el.querySelector(".o_field_widget[name=float_field] input"),
            "o_field_invalid",
            "fload field should be displayed as invalid"
        );
        assert.hasClass(
            form.el.querySelector(".o_form_view"),
            "o_form_editable",
            "form view should still be editable"
        );

        await editInput(form.el, ".o_field_widget[name=float_field] input", "=3:2?+4");
        await click(form.el, ".o_form_button_save");

        assert.hasClass(
            form.el.querySelector(".o_form_view"),
            "o_form_editable",
            "form view should still be editable"
        );
        assert.hasClass(
            form.el.querySelector(".o_field_widget[name=float_field] input"),
            "o_field_invalid",
            "float field should be displayed as invalid"
        );
    });

    QUnit.skipWOWL("float field in editable list view", async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                '<field name="float_field" widget="float" digits="[5,3]"/>' +
                "</tree>",
        });

        var zeroValues = list.el.querySelector("td.o_data_cell").filter(function () {
            return $(this).text() === "";
        });
        assert.strictEqual(
            zeroValues.length,
            1,
            "Unset float values should be rendered as empty strings."
        );

        // switch to edit mode
        var $cell = list.el.querySelector("tr.o_data_row td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);

        assert.containsOnce(
            list,
            'input[name="float_field"]',
            "The view should have 1 input for editable float."
        );

        await testUtils.fields.editInput(
            list.el.querySelector('input[name="float_field"]'),
            "108.2458938598598"
        );
        assert.strictEqual(
            list.el.querySelector('input[name="float_field"]').value,
            "108.2458938598598",
            "The value should not be formated yet."
        );

        await testUtils.fields.editInput(
            list.el.querySelector('input[name="float_field"]'),
            "18.8958938598598"
        );
        await testUtils.dom.click(list.el.querySelectorbuttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.el.querySelector(".o_field_widget").textContent,
            "18.896",
            "The new value should be rounded properly."
        );

        list.destroy();
    });

    QUnit.skipWOWL(
        "do not trigger a field_changed if they have not changed",
        async function (assert) {
            assert.expect(2);

            this.data.partner.records[1].float_field = false;
            this.data.partner.records[1].int_field = false;
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    '<field name="float_field" widget="float" digits="[5,3]"/>' +
                    '<field name="int_field"/>' +
                    "</sheet>" +
                    "</form>",
                res_id: 2,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            await testUtils.form.clickEdit(form);
            await testUtils.form.clickSave(form);

            assert.verifySteps(["read"]); // should not have save as nothing changed

            form.destroy();
        }
    );

    QUnit.skipWOWL("float widget on monetary field", async function (assert) {
        assert.expect(1);

        this.data.partner.fields.monetary = { string: "Monetary", type: "monetary" };
        this.data.partner.records[0].monetary = 9.99;
        this.data.partner.records[0].currency_id = 1;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="monetary" widget="float"/>' +
                '<field name="currency_id" invisible="1"/>' +
                "</sheet>" +
                "</form>",
            res_id: 1,
            session: {
                currencies: _.indexBy(this.data.currency.records, "id"),
            },
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=monetary]").text(),
            "9.99",
            "value should be correctly formatted (with the float formatter)"
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "float field with monetary widget and decimal precision",
        async function (assert) {
            assert.expect(5);

            this.data.partner.records = [
                {
                    id: 1,
                    float_field: -8.89859,
                    currency_id: 1,
                },
            ];
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    '<field name="float_field" widget="monetary" options="{\'field_digits\': True}"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                    "</sheet>" +
                    "</form>",
                res_id: 1,
                session: {
                    currencies: _.indexBy(this.data.currency.records, "id"),
                },
            });

            // Non-breaking space between the currency and the amount
            assert.strictEqual(
                form.el.querySelector(".o_field_widget").textContent,
                "$\u00a0-8.9",
                "The value should be displayed properly."
            );

            await testUtils.form.clickEdit(form);
            assert.strictEqual(
                form.el.querySelector(".o_field_widget[name=float_field] input").value,
                "-8.9",
                "The input should be rendered without the currency symbol."
            );
            assert.strictEqual(
                form.el.querySelector(".o_field_widget[name=float_field] input").parent().children()
                    .textContent,
                "$",
                "The input should be preceded by a span containing the currency symbol."
            );

            await testUtils.fields.editInput(
                form.el.querySelector(".o_field_monetary input"),
                "109.2458938598598"
            );
            assert.strictEqual(
                form.el.querySelector(".o_field_widget[name=float_field] input").value,
                "109.2458938598598",
                "The value should not be formated yet."
            );

            await testUtils.form.clickSave(form);
            // Non-breaking space between the currency and the amount
            assert.strictEqual(
                form.el.querySelector(".o_field_widget").textContent,
                "$\u00a0109.2",
                "The new value should be rounded properly."
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL("float field with type number option", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<field name=\"float_field\" options=\"{'type': 'number'}\"/>" +
                "</form>",
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.ok(
            form.el.querySelector(".o_field_widget")[0].hasAttribute("type"),
            "Float field with option type must have a type attribute."
        );
        assert.hasAttrValue(
            form.el.querySelector(".o_field_widget"),
            "type",
            "number",
            'Float field with option type must have a type attribute equals to "number".'
        );
        await testUtils.fields.editInput(
            form.el.querySelector(".o_field_widget[name=float_field] input"),
            "123456.7890"
        );
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").value,
            "123456.789",
            "Float value must be not formatted if input type is number."
        );
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").text(),
            "123,456.8",
            "Float value must be formatted in readonly view even if the input type is number."
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "float field with type number option and comma decimal separator",
        async function (assert) {
            assert.expect(4);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<field name=\"float_field\" options=\"{'type': 'number'}\"/>" +
                    "</form>",
                res_id: 4,
                translateParameters: {
                    thousands_sep: ".",
                    decimal_point: ",",
                    grouping: [3, 0],
                },
            });

            await testUtils.form.clickEdit(form);
            assert.ok(
                form.el.querySelector(".o_field_widget")[0].hasAttribute("type"),
                "Float field with option type must have a type attribute."
            );
            assert.hasAttrValue(
                form.el.querySelector(".o_field_widget"),
                "type",
                "number",
                'Float field with option type must have a type attribute equals to "number".'
            );
            await testUtils.fields.editInput(
                form.el.querySelector(".o_field_widget[name=float_field] input"),
                "123456.789"
            );
            await testUtils.form.clickSave(form);
            await testUtils.form.clickEdit(form);
            assert.strictEqual(
                form.el.querySelector(".o_field_widget").value,
                "123456.789",
                "Float value must be not formatted if input type is number."
            );
            await testUtils.form.clickSave(form);
            assert.strictEqual(
                form.el.querySelector(".o_field_widget").text(),
                "123.456,8",
                "Float value must be formatted in readonly view even if the input type is number."
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL("float field without type number option", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners">' + '<field name="float_field"/>' + "</form>",
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.hasAttrValue(
            form.el.querySelector(".o_field_widget"),
            "type",
            "text",
            "Float field with option type must have a text type (default type)."
        );

        await testUtils.fields.editInput(
            form.el.querySelector(".o_field_widget[name=float_field] input"),
            "123456.7890"
        );
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").value,
            "123,456.8",
            "Float value must be formatted if input type isn't number."
        );

        form.destroy();
    });
});
