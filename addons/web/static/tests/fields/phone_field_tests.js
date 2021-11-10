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

    QUnit.module("PhoneField");

    QUnit.skip("PhoneField in form view on normal screens", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="phone"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
            config: {
                device: {
                    size_class: config.device.SIZES.LG,
                },
            },
        });

        var $phone = form.$("div.o_field_widget.o_form_uri.o_field_phone > a");
        assert.strictEqual(
            $phone.length,
            1,
            "should have rendered the phone number as a link with correct classes"
        );
        assert.strictEqual($phone.text(), "yop", "value should be displayed properly");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            'input[type="text"].o_field_widget',
            "should have an input for the phone field"
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
        assert.strictEqual(
            form.$("div.o_field_widget.o_form_uri.o_field_phone > a").text(),
            "new",
            "new value should be displayed properly"
        );

        form.destroy();
    });

    QUnit.skip("PhoneField in editable list view on normal screens", async function (assert) {
        assert.expect(8);
        var doActionCount = 0;

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
            config: {
                device: {
                    size_class: config.device.SIZES.LG,
                },
            },
        });

        assert.containsN(list, "tbody td:not(.o_list_record_selector)", 5);
        assert.strictEqual(
            list.$("tbody td:not(.o_list_record_selector) a").first().text(),
            "yop",
            "value should be displayed properly with a link to send SMS"
        );

        assert.containsN(
            list,
            "div.o_field_widget.o_form_uri.o_field_phone > a",
            5,
            "should have the correct classnames"
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
            list.$("tbody td:not(.o_list_record_selector) a").first().text(),
            "new",
            "value should be properly updated"
        );
        assert.containsN(
            list,
            "div.o_field_widget.o_form_uri.o_field_phone > a",
            5,
            "should still have links with correct classes"
        );

        list.destroy();
    });

    QUnit.skip("use TAB to navigate to a PhoneField", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="display_name"/>' +
                '<field name="foo" widget="phone"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
        });

        testUtils.dom.click(form.$("input[name=display_name]"));
        assert.strictEqual(
            form.$('input[name="display_name"]')[0],
            document.activeElement,
            "display_name should be focused"
        );
        form.$('input[name="display_name"]').trigger(
            $.Event("keydown", { which: $.ui.keyCode.TAB })
        );
        assert.strictEqual(
            form.$('input[name="foo"]')[0],
            document.activeElement,
            "foo should be focused"
        );

        form.destroy();
    });
});
