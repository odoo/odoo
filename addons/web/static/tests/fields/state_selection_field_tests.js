/** @odoo-module **/

import { registry } from "@web/core/registry";
import { click, getFixture, nextTick } from "../helpers/utils";
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
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1 },
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

        setupViewRegistries();
    });

    QUnit.module("StateSelectionField");

    QUnit.test("StateSelectionField in form view", async function (assert) {
        assert.expect(21);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="selection" widget="state_selection"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
            /*
            viewOptions: {
                disable_autofocus: true,
            },*/
        });

        assert.containsOnce(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should have one red status since selection is the second, blocked state"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should not have one green status since selection is the second, blocked state"
        );
        assert.containsNone(form, ".dropdown-menu", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await click(target, ".o_field_widget.o_field_state_selection .o_status");
        assert.containsOnce(document.body, ".dropdown-menu", "there should be a dropdown");
        assert.containsN(
            form,
            ".dropdown-menu .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the first option, "Normal"
        await click(target.querySelector(".dropdown-menu .dropdown-item"));
        assert.containsNone(form, ".dropdown-menu", "there should not be a dropdown anymore");
        assert.containsNone(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should not have one red status since selection is the first, normal state"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should not have one green status since selection is the first, normal state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_field_state_selection span.o_status",
            "should have one grey status since selection is the first, normal state"
        );

        // switch to edit mode and check the result
        await click(target.querySelector(".o_form_button_edit"));
        assert.containsNone(form, ".dropdown-menu", "there should still not be a dropdown");
        assert.containsNone(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should still not have one red status since selection is the first, normal state"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should still not have one green status since selection is the first, normal state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_field_state_selection span.o_status",
            "should still have one grey status since selection is the first, normal state"
        );

        // Click on the status button to make the dropdown appear
        await click(target, ".o_field_widget.o_field_state_selection .o_status");
        assert.containsOnce(form, ".dropdown-menu", "there should be a dropdown");
        assert.containsN(
            form,
            ".dropdown-menu .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the last option, "Done"
        await click(target, ".dropdown-menu .dropdown-item:last-child");
        assert.containsNone(form, ".dropdown-menu", "there should not be a dropdown anymore");
        assert.containsNone(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should not have one red status since selection is the third, done state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should have one green status since selection is the third, done state"
        );

        // save
        await click(target.querySelector(".o_form_button_save"));
        assert.containsNone(form, ".dropdown-menu", "there should still not be a dropdown anymore");
        assert.containsNone(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should still not have one red status since selection is the third, done state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should still have one green status since selection is the third, done state"
        );
    });

    QUnit.test("StateSelectionField with readonly modifier", async function (assert) {
        assert.expect(4);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="selection" widget="state_selection" readonly="1"/></form>',
            resId: 1,
        });

        assert.hasClass(target.querySelector(".o_field_state_selection"), "o_readonly_modifier");
        assert.hasClass(target.querySelector(".o_field_state_selection button"), "disabled");
        assert.isNotVisible(target.querySelector(".dropdown-menu"));
        await click(target, ".o_field_state_selection span.o_status");
        assert.isNotVisible(target.querySelector(".dropdown-menu"));
    });

    QUnit.test("StateSelectionField for list view with hide_label option", async function (assert) {
        assert.expect(6);

        Object.assign(serverData.models.partner.fields, {
            graph_type: {
                string: "Graph Type",
                type: "selection",
                selection: [
                    ["line", "Line"],
                    ["bar", "Bar"],
                ],
            },
        });
        serverData.models.partner.records[0].graph_type = "bar";
        serverData.models.partner.records[1].graph_type = "line";

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
                    <field name="graph_type" widget="state_selection" options="{'hide_label': True}"/>
                    <field name="selection" widget="state_selection"/>
                </tree>`,
        });

        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            10,
            "should have ten status selection widgets"
        );
        const selection = Array.from(
            target.querySelectorAll(
                ".o_state_selection_cell .o_field_state_selection[name=selection] span.o_status_label"
            )
        );
        assert.strictEqual(selection.length, 5, "should have five label on selection widgets");
        assert.strictEqual(
            selection.filter((el) => el.innerText === "Done").length,
            1,
            "should have one Done status label"
        );
        assert.strictEqual(
            selection.filter((el) => el.innerText === "Normal").length,
            3,
            "should have three Normal status label"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection[name=graph_type] span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_field_state_selection[name=graph_type] span.o_status_label",
            "should not have status label in selection widgets"
        );
    });

    QUnit.skipWOWL("StateSelectionField in editable list view", async function (assert) {
        assert.expect(33);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch:
                '<tree editable="bottom">' +
                '<field name="foo"/>' +
                '<field name="selection" widget="state_selection"/>' +
                "</tree>",
        });

        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should have one red status"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            "should have one green status"
        );
        assert.containsNone(list, ".dropdown-menu", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        let cell = target.querySelector("tbody td.o_state_selection_cell");
        await click(
            target.querySelector(".o_state_selection_cell .o_field_state_selection span.o_status")
        );
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode since we clicked on the state selection widget"
        );
        assert.containsOnce(list, ".dropdown-menu", "there should be a dropdown");
        assert.containsN(
            list,
            ".dropdown-menu .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the first option, "Normal"
        await click(target.querySelector(".dropdown-menu .dropdown-item"));
        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should now have no red status"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            "should still have one green status"
        );
        assert.containsNone(list, ".dropdown-menu", "there should not be a dropdown");
        assert.containsNone(list, "tr.o_selected_row", "should not be in edit mode");

        // switch to edit mode and check the result
        cell = target.querySelector("tbody td.o_state_selection_cell");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should now be in edit mode");
        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should now have no red status"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            "should still have one green status"
        );
        assert.containsNone(list, ".dropdown-menu", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await click(
            target.querySelector(".o_state_selection_cell .o_field_state_selection span.o_status")
        );
        assert.containsOnce(list, ".dropdown-menu", "there should be a dropdown");
        assert.containsN(
            list,
            ".dropdown-menu .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on another row
        const lastCell = target.querySelector("tbody td.o_state_selection_cell:last-child");
        await click(lastCell);
        assert.containsNone(list, ".dropdown-menu", "there should not be a dropdown anymore");
        const firstCell = target.querySelector("tbody td.o_state_selection_cell");
        assert.doesNotHaveClass(
            firstCell.parentElement,
            "o_selected_row",
            "first row should not be in edit mode anymore"
        );
        assert.hasClass(
            lastCell.parentElement,
            "o_selected_row",
            "last row should be in edit mode"
        );

        // Click on the last status button to make the dropdown appear
        await click(
            target.querySelectorAll(
                ".o_state_selection_cell .o_field_state_selection span.o_status"
            )[4]
        );
        assert.containsOnce(list, ".dropdown-menu", "there should be a dropdown");
        assert.containsN(
            list,
            ".dropdown-menu .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the last option, "Done"
        await click(target, ".dropdown-menu .dropdown-item:last-child");
        assert.containsNone(list, ".dropdown-menu", "there should not be a dropdown anymore");
        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should still have no red status"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            2,
            "should now have two green status"
        );
        assert.containsNone(list, ".dropdown-menu", "there should not be a dropdown");

        // save
        await click(target.querySelector(".o_list_button_save"));
        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should have no red status"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            2,
            "should have two green status"
        );
        assert.containsNone(list, ".dropdown-menu", "there should not be a dropdown");
    });

    QUnit.skipWOWL(
        'StateSelectionField edited by the smart action "Set kanban state..."',
        async function (assert) {
            assert.expect(4);

            const legacyEnv = makeTestEnvironment({ bus: core.bus });
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

            const views = {
                "partner,false,form":
                    "<form>" + '<field name="selection" widget="state_selection"/>' + "</form>",
                "partner,false,search": "<search></search>",
            };
            const serverData = { models: serverData.models, views };
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                res_id: 1,
                type: "ir.actions.act_window",
                target: "current",
                res_model: "partner",
                view_mode: "form",
                views: [[false, "form"]],
            });
            assert.containsOnce(webClient, ".o_status_red");

            triggerHotkey("control+k");
            await nextTick();
            const idx = [...webClient.el.querySelectorAll(".o_command")]
                .map((el) => el.textContent)
                .indexOf("Set kanban state...ALT + SHIFT + R");
            assert.ok(idx >= 0);

            await click([...webClient.el.querySelectorAll(".o_command")][idx]);
            await nextTick();
            assert.deepEqual(
                [...webClient.el.querySelectorAll(".o_command")].map((el) => el.textContent),
                ["Normal", "Blocked", "Done"]
            );
            await click(webClient.el, "#o_command_2");
            await legacyExtraNextTick();
            assert.containsOnce(webClient, ".o_status_green");
        }
    );
});
