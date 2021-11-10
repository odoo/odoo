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

    QUnit.module("EmailField");

    QUnit.skip("EmailField in form view", async function (assert) {
        assert.expect(7);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        var $mailtoLink = form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_email > a");
        assert.strictEqual($mailtoLink.length, 1, "should have a anchor with correct classes");
        assert.strictEqual($mailtoLink.text(), "yop", "the value should be displayed properly");
        assert.hasAttrValue($mailtoLink, "href", "mailto:yop", "should have proper mailto prefix");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            'input[type="text"].o_field_widget',
            "should have an input for the email field"
        );
        assert.strictEqual(
            form.$('input[type="text"].o_field_widget').val(),
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        await testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), "new");

        // save
        await testUtils.form.clickSave(form);
        $mailtoLink = form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_email > a");
        assert.strictEqual($mailtoLink.text(), "new", "new value should be displayed properly");
        assert.hasAttrValue(
            $mailtoLink,
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );

        form.destroy();
    });

    QUnit.skip("EmailField in editable list view", async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"  widget="email"/></tree>',
        });

        assert.strictEqual(
            list.$("tbody td:not(.o_list_record_selector)").length,
            5,
            "should have 5 cells"
        );
        assert.strictEqual(
            list.$("tbody td:not(.o_list_record_selector)").first().text(),
            "yop",
            "value should be displayed properly as text"
        );

        var $mailtoLink = list.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_email > a");
        assert.strictEqual($mailtoLink.length, 5, "should have anchors with correct classes");
        assert.hasAttrValue(
            $mailtoLink.first(),
            "href",
            "mailto:yop",
            "should have proper mailto prefix"
        );

        // Edit a line and check the result
        var $cell = list.$("tbody td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(), "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            $cell.find("input").val(),
            "yop",
            "should have the corect value in internal input"
        );
        await testUtils.fields.editInput($cell.find("input"), "new");

        // save
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        $cell = list.$("tbody td:not(.o_list_record_selector)").first();
        assert.doesNotHaveClass(
            $cell.parent(),
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            list.$("tbody td:not(.o_list_record_selector)").first().text(),
            "new",
            "value should be properly updated"
        );
        $mailtoLink = list.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_email > a");
        assert.strictEqual($mailtoLink.length, 5, "should still have anchors with correct classes");
        assert.hasAttrValue(
            $mailtoLink.first(),
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );

        list.destroy();
    });

    QUnit.skip("EmailField with empty value", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="empty_string" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        var $mailtoLink = form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_email > a");
        assert.strictEqual($mailtoLink.text(), "", "the value should be displayed properly");

        form.destroy();
    });

    QUnit.skip("EmailField trim user value", async function (assert) {
        assert.expect(1);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="foo" widget="email"/></form>',
            res_id: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        await testUtils.fields.editInput(form.$('input[name="foo"]'), "  abc@abc.com  ");
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$('input[name="foo"]').val(),
            "abc@abc.com",
            "Foo value should have been trimmed"
        );

        form.destroy();
    });

    QUnit.skip(
        "readonly EmailField is properly rerendered after been changed by onchange",
        async function (assert) {
            assert.expect(2);

            this.data.partner.records[0].foo = "dolores.abernathy@delos";
            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    "<group>" +
                    '<field name="int_field" on_change="1"/>' + // onchange to update mobile in readonly mode directly
                    '<field name="foo" widget="email" readonly="1"/>' + // readonly only, we don't want to go through write mode
                    "</group>" +
                    "</sheet>" +
                    "</form>",
                res_id: 1,
                viewOptions: { mode: "edit" },
                mockRPC: function (route, args) {
                    if (args.method === "onchange") {
                        return Promise.resolve({
                            value: {
                                foo: "lara.espin@unknown", // onchange to update foo in readonly mode directly
                            },
                        });
                    }
                    return this._super.apply(this, arguments);
                },
            });
            // check initial rendering
            assert.strictEqual(
                form.$(".o_field_email").text(),
                "dolores.abernathy@delos",
                "Initial email text should be set"
            );

            // trigger the onchange to update phone field, but still in readonly mode
            await testUtils.fields.editInput($('input[name="int_field"]'), "3");

            // check rendering after changes
            assert.strictEqual(
                form.$(".o_field_email").text(),
                "lara.espin@unknown",
                "email text should be updated"
            );

            form.destroy();
        }
    );
});
