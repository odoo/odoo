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

    QUnit.test("EmailField in form view", async function (assert) {
        assert.expect(7);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
        });
        let mailtoLink = form.el.querySelector("a.o-email-field.o_form_uri.o_text_overflow");
        assert.containsOnce(form, mailtoLink, "should have a anchor with correct classes");
        assert.strictEqual(mailtoLink.innerText, "yop", "the value should be displayed properly");
        assert.hasAttrValue(mailtoLink, "href", "mailto:yop", "should have proper mailto prefix");

        // switch to edit mode and check the result
        await click(form.el.querySelector(".o_form_button_edit"));
        const mailtoEdit = form.el.querySelector('input[type="email"].o-email-field');
        assert.containsOnce(form, mailtoEdit, "should have an input for the email field");
        assert.strictEqual(
            mailtoEdit.value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        mailtoEdit.value = "new";
        await triggerEvent(mailtoEdit, null, "change");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        mailtoLink = form.el.querySelector("a.o-email-field");
        assert.strictEqual(mailtoLink.innerText, "new", "new value should be displayed properly");
        assert.hasAttrValue(
            mailtoLink,
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );

        form.destroy();
    });

    QUnit.skip("EmailField in editable list view", async function (assert) {
        assert.expect(10);

        var list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree edit="1" editable="bottom"><field name="foo"  widget="email"/></tree>',
        });

        assert.strictEqual(
            list.el.querySelectorAll("tbody td:not(.o_list_record_selector)").length,
            5,
            "should have 5 cells"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").innerText,
            "yop",
            "value should be displayed properly as text"
        );

        var mailtoLink = list.el.querySelectorAll("a.o-email-field");
        assert.strictEqual(mailtoLink.length, 5, "should have anchors with correct classes");
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:yop",
            "should have proper mailto prefix"
        );
        // Edit a line and check the result
        var cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        const mailField = cell.querySelector("input");
        assert.strictEqual(
            mailField.value,
            "yop",
            "should have the correct value in internal input"
        );
        mailField.value = "new";
        await triggerEvent(mailField, null, "change");

        // save
        await click(list.buttons.find(".o_list_button_save"));
        cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").innerText,
            "new",
            "value should be properly updated"
        );
        mailtoLink = list.el.querySelectorAll(
            "div.o_form_uri.o_field_widget.o_text_overflow.o-email-field > a"
        );
        assert.strictEqual(mailtoLink.length, 5, "should still have anchors with correct classes");
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );

        list.destroy();
    });

    QUnit.test("EmailField with empty value", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="empty_string" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
        });

        await click(form.el.querySelector(".o_form_button_save"));
        const mailtoLink = form.el.querySelector("a.o-email-field");
        assert.strictEqual(mailtoLink.innerText, "", "the value should be displayed properly");

        form.destroy();
    });

    QUnit.test("EmailField trim user value", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="foo" widget="email"/></form>',
        });
        const mailField = form.el.querySelector('input[name="foo"]');
        mailField.value = "  abc@abc.com  ";
        await triggerEvent(mailField, null, "change");
        await click(form.el.querySelector(".o_form_button_save"));
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.strictEqual(mailField.value, "abc@abc.com", "Foo value should have been trimmed");

        form.destroy();
    });

    QUnit.test(
        "readonly EmailField is properly rerendered after been changed by onchange",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].foo = "dolores.abernathy@delos";
            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    "<group>" +
                    '<field name="int_field" on_change="1"/>' + // onchange to update mobile in readonly mode directly
                    '<field name="foo" widget="email" readonly="1"/>' + // readonly only, we don't want to go through write mode
                    "</group>" +
                    "</sheet>" +
                    "</form>",
                resId: 1,
                mockRPC(route, { method }) {
                    if (method === "onchange") {
                        return Promise.resolve({
                            value: {
                                foo: "lara.espin@unknown", // onchange to update foo in readonly mode directly
                            },
                        });
                    }
                },
            });
            // check initial rendering
            assert.strictEqual(
                form.el.querySelector(".o-email-field").innerText,
                "dolores.abernathy@delos",
                "Initial email text should be set"
            );

            // edit the phone field, but with the mail in readonly mode
            await click(form.el.querySelector(".o_form_button_edit"));
            const field = form.el.querySelector('input[name="int_field"]');
            field.value = "3";
            await triggerEvent(field, null, "change");
            await click(form.el.querySelector(".o_form_button_save"));

            // check rendering after changes
            assert.strictEqual(
                form.el.querySelector(".o-email-field").innerText,
                "lara.espin@unknown",
                "email text should be updated"
            );

            form.destroy();
        }
    );
});
