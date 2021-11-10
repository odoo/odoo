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

    QUnit.module("BooleanField");

    QUnit.test("boolean field in form view", async function (assert) {
        assert.expect(15);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <label for="bar" string="Awesome checkbox" />
                    <field name="bar" />
                </form>
            `,
        });

        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should be checked"
        );
        assert.containsNone(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should not be disabled"
        );

        // switch to edit mode and check the result
        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsNone(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should not be disabled"
        );

        // uncheck the checkbox
        await click(form.el, ".o_field_boolean input:checked");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should no longer be checked"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still no longer be checked"
        );

        // switch to edit mode and test the opposite change
        await click(form.el, ".o_form_button_edit");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be unchecked"
        );

        // check the checkbox
        await click(form.el, ".o_field_boolean input");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // uncheck it back
        await click(form.el, ".o_field_boolean input");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be unchecked"
        );

        // check the checkbox by clicking on label
        await click(form.el, ".o_form_view label:not(.custom-control-label)");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // uncheck it back
        await click(form.el, ".o_form_view label:not(.custom-control-label)");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be unchecked"
        );

        // check the checkbox by hitting the "enter" key after focusing it
        await triggerEvents(form.el, ".o_field_boolean input", [
            ["focusin"],
            ["keydown", { key: "Enter" }],
            ["keyup", { key: "Enter" }],
        ]);
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // blindly press enter again, it should uncheck the checkbox
        await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should not be checked"
        );
        await nextTick();
        // blindly press enter again, it should check the checkbox back
        await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
    });

    QUnit.skip("boolean field in editable list view", async function (assert) {
        assert.expect(11);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="bar" />
                </tree>
            `,
        });

        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            4,
            "should have 4 checked input"
        );

        // Edit a line
        let cell = list.el.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.ok(
            cell.querySelector(".custom-checkbox input:checked").disabled,
            "input should be disabled in readonly mode"
        );
        await click(cell);
        assert.notOk(
            cell.querySelector(".custom-checkbox input:checked").disabled,
            "input should not have the disabled property in edit mode"
        );
        await click(cell, ".custom-checkbox input:checked");

        // save
        await click(list, ".o_list_button_save");
        cell = list.el.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.ok(
            cell.querySelector(".custom-checkbox input:not(:checked)").disabled,
            "input should be disabled again"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            3,
            "should now have only 3 checked input"
        );

        // Re-Edit the line and fake-check the checkbox
        await click(cell);
        await click(cell, ".custom-checkbox input");
        await click(cell, ".custom-checkbox input");

        // Save
        await click(list, ".o_list_button_save");
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            3,
            "should still have only 3 checked input"
        );

        // Re-Edit the line to check the checkbox back but this time click on
        // the checkbox directly in readonly mode !
        cell = list.el.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        await click(cell, ".custom-checkbox .custom-control-label");
        await nextTick();

        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            4,
            "should now have 4 checked input back"
        );
    });

    QUnit.test("readonly boolean field", async function (assert) {
        assert.expect(6);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="bar" readonly="1" />
                </form>
            `,
        });

        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should be checked"
        );
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should be disabled"
        );

        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should still be disabled"
        );

        await click(form.el, ".o_field_boolean label");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should still be disabled"
        );
    });
});
