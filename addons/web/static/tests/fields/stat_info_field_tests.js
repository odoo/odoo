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

    QUnit.module("StatInfoField");

    QUnit.skip("StatInfoField formats decimal precision", async function (assert) {
        // sometimes the round method can return numbers such as 14.000001
        // when asked to round a number to 2 decimals, as such is the behaviour of floats.
        // we check that even in that eventuality, only two decimals are displayed
        assert.expect(2);

        this.data.partner.fields.monetary = { string: "Monetary", type: "monetary" };
        this.data.partner.records[0].monetary = 9.999999;
        this.data.partner.records[0].currency_id = 1;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<button class="oe_stat_button" name="items" icon="fa-gear">' +
                '<field name="qux" widget="statinfo"/>' +
                "</button>" +
                '<button class="oe_stat_button" name="money" icon="fa-money">' +
                '<field name="monetary" widget="statinfo"/>' +
                "</button>" +
                "</form>",
            res_id: 1,
        });

        // formatFloat renders according to this.field.digits
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").eq(0).text(),
            "0.4",
            "Default precision should be [16,1]"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").eq(1).text(),
            "10.00",
            "Currency decimal precision should be 2"
        );

        form.destroy();
    });

    QUnit.skip("StatInfoField in form view", async function (assert) {
        assert.expect(9);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<div class="oe_button_box" name="button_box">' +
                '<button class="oe_stat_button" name="items"  type="object" icon="fa-gear">' +
                '<field name="int_field" widget="statinfo"/>' +
                "</button>" +
                "</div>" +
                "<group>" +
                '<field name="foo"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "int_field",
            "should have 'int_field' as text"
        );

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should still have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should still have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "int_field",
            "should have 'int_field' as text"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "int_field",
            "should have 'int_field' as text"
        );

        form.destroy();
    });

    QUnit.skip("StatInfoField in form view with specific label_field", async function (assert) {
        assert.expect(9);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<div class="oe_button_box" name="button_box">' +
                '<button class="oe_stat_button" name="items"  type="object" icon="fa-gear">' +
                '<field string="Useful stat button" name="int_field" widget="statinfo" ' +
                "options=\"{'label_field': 'foo'}\"/>" +
                "</button>" +
                "</div>" +
                "<group>" +
                '<field name="foo" invisible="1"/>' +
                '<field name="bar"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "yop",
            "should have 'yop' as text, since it is the value of field foo"
        );

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should still have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should still have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "yop",
            "should have 'yop' as text, since it is the value of field foo"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "yop",
            "should have 'yop' as text, since it is the value of field foo"
        );

        form.destroy();
    });

    QUnit.skip("StatInfoField in form view with no label", async function (assert) {
        assert.expect(9);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<div class="oe_button_box" name="button_box">' +
                '<button class="oe_stat_button" name="items"  type="object" icon="fa-gear">' +
                '<field string="Useful stat button" name="int_field" widget="statinfo" nolabel="1"/>' +
                "</button>" +
                "</div>" +
                "<group>" +
                '<field name="foo" invisible="1"/>' +
                '<field name="bar"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "",
            "should not have any label"
        );

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should still have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should still have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "",
            "should not have any label"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value").text(),
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.$(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text").text(),
            "",
            "should not have any label"
        );

        form.destroy();
    });
});
