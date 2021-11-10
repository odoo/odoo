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

    QUnit.module("IntegerField");

    QUnit.skip("IntegerField when unset", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="int_field"/></form>',
            res_id: 4,
        });

        assert.doesNotHaveClass(
            form.$(".o_field_widget"),
            "o_field_empty",
            "Non-set integer field should be recognized as 0."
        );
        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "0",
            "Non-set integer field should be recognized as 0."
        );

        form.destroy();
    });

    QUnit.skip("IntegerField in form view", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="int_field"/></form>',
            res_id: 2,
        });

        assert.doesNotHaveClass(
            form.$(".o_field_widget"),
            "o_field_empty",
            "Integer field should be considered set for value 0."
        );

        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$("input[name=int_field]").val(),
            "0",
            "The value should be rendered correctly in edit mode."
        );

        await testUtils.fields.editInput(form.$("input[name=int_field]"), "-18");
        assert.strictEqual(
            form.$("input[name=int_field]").val(),
            "-18",
            "The value should be correctly displayed in the input."
        );

        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "-18",
            "The new value should be saved and displayed properly."
        );

        form.destroy();
    });

    QUnit.skip("IntegerField rounding using formula in form view", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="int_field"/></form>',
            res_id: 2,
        });

        // Test computation and rounding
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$("input[name=int_field]"), "=100/3");
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").first().text(),
            "33",
            "The new value should be calculated properly."
        );

        form.destroy();
    });

    QUnit.skip("IntegerField in form view with virtual id", async function (assert) {
        assert.expect(1);
        var params = {
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="id"/></form>',
        };

        params.res_id = this.data.partner.records[1].id = "2-20170808020000";
        var form = await createView(params);
        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "2-20170808020000",
            "Should display virtual id"
        );

        form.destroy();
    });

    QUnit.skip("IntegerField in editable list view", async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom">' + '<field name="int_field"/>' + "</tree>",
        });

        var zeroValues = list.$("td").filter(function () {
            return $(this).text() === "0";
        });
        assert.strictEqual(
            zeroValues.length,
            1,
            "Unset integer values should not be rendered as zeros."
        );

        // switch to edit mode
        var $cell = list.$("tr.o_data_row td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);

        assert.containsOnce(
            list,
            'input[name="int_field"]',
            "The view should have 1 input for editable integer."
        );

        await testUtils.fields.editInput(list.$('input[name="int_field"]'), "-28");
        assert.strictEqual(
            list.$('input[name="int_field"]').val(),
            "-28",
            "The value should be displayed properly in the input."
        );

        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.$("td:not(.o_list_record_selector)").first().text(),
            "-28",
            "The new value should be saved and displayed properly."
        );

        list.destroy();
    });

    QUnit.skip("IntegerField with type number option", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<field name=\"int_field\" options=\"{'type': 'number'}\"/>" +
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
            "Integer field with option type must have a type attribute."
        );
        assert.hasAttrValue(
            form.$(".o_field_widget"),
            "type",
            "number",
            'Integer field with option type must have a type attribute equals to "number".'
        );

        await testUtils.fields.editInput(form.$("input[name=int_field]"), "1234567890");
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget").val(),
            "1234567890",
            "Integer value must be not formatted if input type is number."
        );
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget").text(),
            "1,234,567,890",
            "Integer value must be formatted in readonly view even if the input type is number."
        );

        form.destroy();
    });

    QUnit.skip("IntegerField without type number option", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners">' + '<field name="int_field"/>' + "</form>",
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
            "Integer field without option type must have a text type (default type)."
        );

        await testUtils.fields.editInput(form.$("input[name=int_field]"), "1234567890");
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget").val(),
            "1,234,567,890",
            "Integer value must be formatted if input type isn't number."
        );

        form.destroy();
    });

    QUnit.skip("IntegerField without formatting", async function (assert) {
        assert.expect(3);

        this.data.partner.records = [
            {
                id: 999,
                int_field: 8069,
            },
        ];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<field name=\"int_field\" options=\"{'format': 'false'}\"/>" +
                "</form>",
            res_id: 999,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        assert.ok(form.$(".o_form_view").hasClass("o_form_readonly"), "Form in readonly mode");
        assert.strictEqual(
            form.$(".o_field_widget[name=int_field]").text(),
            "8069",
            "Integer value must not be formatted"
        );
        await testUtils.form.clickEdit(form);

        assert.strictEqual(
            form.$(".o_field_widget").val(),
            "8069",
            "Integer value must not be formatted"
        );

        form.destroy();
    });

    QUnit.skip("IntegerField is formatted by default", async function (assert) {
        assert.expect(3);

        this.data.partner.records = [
            {
                id: 999,
                int_field: 8069,
            },
        ];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners">' + '<field name="int_field" />' + "</form>",
            res_id: 999,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });
        assert.ok(form.$(".o_form_view").hasClass("o_form_readonly"), "Form in readonly mode");
        assert.strictEqual(
            form.$(".o_field_widget[name=int_field]").text(),
            "8,069",
            "Integer value must be formatted by default"
        );
        await testUtils.form.clickEdit(form);

        assert.strictEqual(
            form.$(".o_field_widget").val(),
            "8,069",
            "Integer value must be formatted by default"
        );

        form.destroy();
    });
});
