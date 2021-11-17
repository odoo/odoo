/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeUserService } from "../helpers/mock_services";
import { click, nextTick, triggerEvent } from "../helpers/utils";
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
                            type: "phone",
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
        assert.expect(7);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="phone"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
            // config: {
            //     device: {
            //         size_class: config.device.SIZES.LG,
            //     },
            // },
        });

        var phone = form.el.querySelector("a.o-phone-field");
        assert.containsOnce(
            form,
            phone,
            "should have rendered the phone number as a link with correct classes"
        );
        assert.strictEqual(phone.innerText, "yop", "value should be displayed properly");
        assert.hasAttrValue(phone, "href", "tel:yop", "should have proper tel prefix");
        // verify the presence of the sms link next to the phone
        assert.hasAttrValue(phone.nextSibling, "href", "sms:yop", "should have proper sms prefix");

        // switch to edit mode and check the result
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.containsOnce(
            form,
            'input[type="phone"].o_field_widget',
            "should have an input for the phone field"
        );
        assert.strictEqual(
            form.el.querySelector('input[type="phone"].o_field_widget').value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        const field = form.el.querySelector('input[type="phone"].o_field_widget');
        field.value = "new";
        await triggerEvent(field, null, "change");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        assert.strictEqual(
            form.el.querySelector("a.o-phone-field").innerText,
            "new",
            "new value should be displayed properly"
        );

        form.destroy();
    });

    QUnit.skip("PhoneField in editable list view on normal screens", async function (assert) {
        assert.expect(8);

        var list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
            // config: {
            //     device: {
            //         size_class: config.device.SIZES.LG,
            //     },
            // },
        });

        assert.containsN(list, "tbody td:not(.o_list_record_selector)", 5);
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector) a").innerText,
            "yop",
            "value should be displayed properly with a link to send SMS"
        );

        assert.containsN(
            list,
            "a.o_field_widget.o_form_uri.o-phone-field",
            5,
            "should have the correct classnames"
        );

        // Edit a line and check the result
        var cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parent(), "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            cell.find("input").value,
            "yop",
            "should have the corect value in internal input"
        );
        const inputField = cell.querySelector("input");
        inputField.value = "new";
        await triggerEvent(inputField, null, "change");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector) a").innerText,
            "new",
            "value should be properly updated"
        );
        assert.containsN(
            list,
            "a.o_field_widget.o_form_uri.o-phone-field",
            5,
            "should still have links with correct classes"
        );

        list.destroy();
    });

    QUnit.skip("use TAB to navigate to a PhoneField", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
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
        await click(form.el.querySelector("input[name=display_name]"));
        assert.strictEqual(
            document.activeElement,
            form.el.querySelector('input[name="display_name"]'),
            "display_name should be focused"
        );
        await triggerEvent(form.el, 'input[name="display_name"]', "keydown", {
            key: "Tab",
        });
        assert.strictEqual(
            document.activeElement,
            form.el.querySelector('input[name="foo"]'),
            "foo should be focused"
        );

        form.destroy();
    });
});
