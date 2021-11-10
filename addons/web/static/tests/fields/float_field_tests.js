/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import { click, makeDeferred, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { makeView } from "../views/helpers";

const serviceRegistry = registry.category("services");

let serverData;

function hasGroup(group) {
    return group === "base.group_allow_export";
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        txt: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                        document: { string: "Binary", type: "binary" },
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            selection: "blocked",
                            document: "coucou==\n",
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                            qux: 0,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            sequence: 4,
                            currency_id: 2,
                            selection: "normal",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            sequence: 9,
                            int_field: false,
                            qux: false,
                            selection: "done",
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, currency_id: 1 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
                        },
                        {
                            id: 2,
                            display_name: "€",
                            symbol: "€",
                            position: "after",
                        },
                    ],
                },
                "ir.translation": {
                    fields: {
                        lang: { type: "char" },
                        value: { type: "char" },
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 37,
                            value: "",
                            lang: "en_US",
                        },
                    ],
                },
            },
        };

        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
    });

    QUnit.module("FloatField");

    QUnit.skip("float field when unset", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" digits="[5,3]"/>' +
                "</sheet>" +
                "</form>",
            res_id: 4,
        });

        assert.doesNotHaveClass(
            form.$(".o_field_widget"),
            "o_field_empty",
            "Non-set float field should be considered as 0."
        );
        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "0.000",
            "Non-set float field should be considered as 0."
        );

        form.destroy();
    });

    QUnit.skip("float fields use correct digit precision", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="qux"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });
        assert.strictEqual(
            form.$("span.o_field_number:contains(0.4)").length,
            1,
            "should contain a number rounded to 1 decimal"
        );
        form.destroy();
    });

    QUnit.skip("float field in list view no widget", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" digits="[5,3]"/>' +
                "</sheet>" +
                "</form>",
            res_id: 2,
        });

        assert.doesNotHaveClass(
            form.$(".o_field_widget"),
            "o_field_empty",
            "Float field should be considered set for value 0."
        );
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "0.000",
            "The value should be displayed properly."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$("input[name=qux]").val(),
            "0.000",
            "The value should be rendered with correct precision."
        );

        await testUtils.fields.editInput(form.$("input[name=qux]"), "108.2458938598598");
        assert.strictEqual(
            form.$("input[name=qux]").val(),
            "108.2458938598598",
            "The value should not be formated yet."
        );

        await testUtils.fields.editInput(form.$("input[name=qux]"), "18.8958938598598");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "18.896",
            "The new value should be rounded properly."
        );

        form.destroy();
    });

    QUnit.skip("float field in form view", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="float" digits="[5,3]"/>' +
                "</sheet>" +
                "</form>",
            res_id: 2,
        });

        assert.doesNotHaveClass(
            form.$(".o_field_widget"),
            "o_field_empty",
            "Float field should be considered set for value 0."
        );
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "0.000",
            "The value should be displayed properly."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$("input[name=qux]").val(),
            "0.000",
            "The value should be rendered with correct precision."
        );

        await testUtils.fields.editInput(form.$("input[name=qux]"), "108.2458938598598");
        assert.strictEqual(
            form.$("input[name=qux]").val(),
            "108.2458938598598",
            "The value should not be formated yet."
        );

        await testUtils.fields.editInput(form.$("input[name=qux]"), "18.8958938598598");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "18.896",
            "The new value should be rounded properly."
        );

        form.destroy();
    });

    QUnit.skip("float field using formula in form view", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="float" digits="[5,3]"/>' +
                "</sheet>" +
                "</form>",
            res_id: 2,
        });

        // Test computation with priority of operation
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$("input[name=qux]"), "=20+3*2");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "26.000",
            "The new value should be calculated properly."
        );

        // Test computation with ** operand
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$("input[name=qux]"), "=2**3");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "8.000",
            "The new value should be calculated properly."
        );

        // Test computation with ^ operant which should do the same as **
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$("input[name=qux]"), "=2^3");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "8.000",
            "The new value should be calculated properly."
        );

        // Test computation and rounding
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$("input[name=qux]"), "=100/3");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "33.333",
            "The new value should be calculated properly."
        );

        form.destroy();
    });

    QUnit.skip("float field using incorrect formula in form view", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="float" digits="[5,3]"/>' +
                "</sheet>" +
                "</form>",
            res_id: 2,
        });

        // Test that incorrect value is not computed
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$("input[name=qux]"), "=abc");
        await testUtils.form.clickSave(form);
        assert.hasClass(
            form.$(".o_form_view"),
            "o_form_editable",
            "form view should still be editable"
        );
        assert.hasClass(
            form.$("input[name=qux]"),
            "o_field_invalid",
            "fload field should be displayed as invalid"
        );

        await testUtils.fields.editInput(form.$("input[name=qux]"), "=3:2?+4");
        await testUtils.form.clickSave(form);
        assert.hasClass(
            form.$(".o_form_view"),
            "o_form_editable",
            "form view should still be editable"
        );
        assert.hasClass(
            form.$("input[name=qux]"),
            "o_field_invalid",
            "float field should be displayed as invalid"
        );

        form.destroy();
    });

    QUnit.skip("float field in editable list view", async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                '<field name="qux" widget="float" digits="[5,3]"/>' +
                "</tree>",
        });

        var zeroValues = list.$("td.o_data_cell").filter(function () {
            return $(this).text() === "";
        });
        assert.strictEqual(
            zeroValues.length,
            1,
            "Unset float values should be rendered as empty strings."
        );

        // switch to edit mode
        var $cell = list.$("tr.o_data_row td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);

        assert.containsOnce(
            list,
            'input[name="qux"]',
            "The view should have 1 input for editable float."
        );

        await testUtils.fields.editInput(list.$('input[name="qux"]'), "108.2458938598598");
        assert.strictEqual(
            list.$('input[name="qux"]').val(),
            "108.2458938598598",
            "The value should not be formated yet."
        );

        await testUtils.fields.editInput(list.$('input[name="qux"]'), "18.8958938598598");
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.$(".o_field_widget").first().text(),
            "18.896",
            "The new value should be rounded properly."
        );

        list.destroy();
    });

    QUnit.skip("do not trigger a field_changed if they have not changed", async function (assert) {
        assert.expect(2);

        this.data.partner.records[1].qux = false;
        this.data.partner.records[1].int_field = false;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="qux" widget="float" digits="[5,3]"/>' +
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
    });

    QUnit.skip("float widget on monetary field", async function (assert) {
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
            form.$(".o_field_widget[name=monetary]").text(),
            "9.99",
            "value should be correctly formatted (with the float formatter)"
        );

        form.destroy();
    });

    QUnit.skip("float field with monetary widget and decimal precision", async function (assert) {
        assert.expect(5);

        this.data.partner.records = [
            {
                id: 1,
                qux: -8.89859,
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
                '<field name="qux" widget="monetary" options="{\'field_digits\': True}"/>' +
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
            form.$(".o_field_widget").first().text(),
            "$\u00a0-8.9",
            "The value should be displayed properly."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "-8.9",
            "The input should be rendered without the currency symbol."
        );
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").parent().children().first().text(),
            "$",
            "The input should be preceded by a span containing the currency symbol."
        );

        await testUtils.fields.editInput(form.$(".o_field_monetary input"), "109.2458938598598");
        assert.strictEqual(
            form.$(".o_field_widget[name=qux] input").val(),
            "109.2458938598598",
            "The value should not be formated yet."
        );

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "$\u00a0109.2",
            "The new value should be rounded properly."
        );

        form.destroy();
    });

    QUnit.skip("float field with type number option", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<field name=\"qux\" options=\"{'type': 'number'}\"/>" +
                "</form>",
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.ok(
            form.$(".o_field_widget")[0].hasAttribute("type"),
            "Float field with option type must have a type attribute."
        );
        assert.hasAttrValue(
            form.$(".o_field_widget"),
            "type",
            "number",
            'Float field with option type must have a type attribute equals to "number".'
        );
        await testUtils.fields.editInput(form.$("input[name=qux]"), "123456.7890");
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget").val(),
            "123456.789",
            "Float value must be not formatted if input type is number."
        );
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "123,456.8",
            "Float value must be formatted in readonly view even if the input type is number."
        );

        form.destroy();
    });

    QUnit.skip(
        "float field with type number option and comma decimal separator",
        async function (assert) {
            assert.expect(4);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<field name=\"qux\" options=\"{'type': 'number'}\"/>" +
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
                form.$(".o_field_widget")[0].hasAttribute("type"),
                "Float field with option type must have a type attribute."
            );
            assert.hasAttrValue(
                form.$(".o_field_widget"),
                "type",
                "number",
                'Float field with option type must have a type attribute equals to "number".'
            );
            await testUtils.fields.editInput(form.$("input[name=qux]"), "123456.789");
            await testUtils.form.clickSave(form);
            await testUtils.form.clickEdit(form);
            assert.strictEqual(
                form.$(".o_field_widget").val(),
                "123456.789",
                "Float value must be not formatted if input type is number."
            );
            await testUtils.form.clickSave(form);
            assert.strictEqual(
                form.$(".o_field_widget").text(),
                "123.456,8",
                "Float value must be formatted in readonly view even if the input type is number."
            );

            form.destroy();
        }
    );

    QUnit.skip("float field without type number option", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners">' + '<field name="qux"/>' + "</form>",
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.hasAttrValue(
            form.$(".o_field_widget"),
            "type",
            "text",
            "Float field with option type must have a text type (default type)."
        );

        await testUtils.fields.editInput(form.$("input[name=qux]"), "123456.7890");
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget").val(),
            "123,456.8",
            "Float value must be formatted if input type isn't number."
        );

        form.destroy();
    });
});
