/** @odoo-module **/

import { registry } from "@web/core/registry";
import { click, nextTick } from "../helpers/utils";
import { setupViewRegistries } from "../views/helpers";

let serverData;

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

        setupViewRegistries();
    });

    QUnit.module("StateSelectionField");

    QUnit.skip("StateSelectionField in form view", async function (assert) {
        assert.expect(21);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="selection" widget="state_selection"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
            viewOptions: {
                disable_autofocus: true,
            },
        });

        assert.containsOnce(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_red",
            "should have one red status since selection is the second, blocked state"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_green",
            "should not have one green status since selection is the second, blocked state"
        );
        assert.containsNone(form, ".dropdown-menu.state:visible", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await testUtils.dom.click(form.$(".o_field_widget.o_selection .o_status").first());
        assert.containsOnce(form, ".dropdown-menu.state:visible", "there should be a dropdown");
        assert.containsN(
            form,
            ".dropdown-menu.state:visible .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the first option, "Normal"
        await testUtils.dom.click(form.$(".dropdown-menu.state:visible .dropdown-item").first());
        assert.containsNone(
            form,
            ".dropdown-menu.state:visible",
            "there should not be a dropdown anymore"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_red",
            "should not have one red status since selection is the first, normal state"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_green",
            "should not have one green status since selection is the first, normal state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_selection > a span.o_status",
            "should have one grey status since selection is the first, normal state"
        );

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsNone(
            form,
            ".dropdown-menu.state:visible",
            "there should still not be a dropdown"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_red",
            "should still not have one red status since selection is the first, normal state"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_green",
            "should still not have one green status since selection is the first, normal state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_selection > a span.o_status",
            "should still have one grey status since selection is the first, normal state"
        );

        // Click on the status button to make the dropdown appear
        await testUtils.dom.click(form.$(".o_field_widget.o_selection .o_status").first());
        assert.containsOnce(form, ".dropdown-menu.state:visible", "there should be a dropdown");
        assert.containsN(
            form,
            ".dropdown-menu.state:visible .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the last option, "Done"
        await testUtils.dom.click(form.$(".dropdown-menu.state:visible .dropdown-item").last());
        assert.containsNone(
            form,
            ".dropdown-menu.state:visible",
            "there should not be a dropdown anymore"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_red",
            "should not have one red status since selection is the third, done state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_green",
            "should have one green status since selection is the third, done state"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.containsNone(
            form,
            ".dropdown-menu.state:visible",
            "there should still not be a dropdown anymore"
        );
        assert.containsNone(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_red",
            "should still not have one red status since selection is the third, done state"
        );
        assert.containsOnce(
            form,
            ".o_field_widget.o_selection > a span.o_status.o_status_green",
            "should still have one green status since selection is the third, done state"
        );

        form.destroy();
    });

    QUnit.skip("StateSelectionField with readonly modifier", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="selection" widget="state_selection" readonly="1"/></form>',
            res_id: 1,
        });

        assert.hasClass(form.$(".o_selection"), "o_readonly_modifier");
        assert.hasClass(form.$(".o_selection > a"), "disabled");
        assert.isNotVisible(form.$(".dropdown-menu.state"));

        await testUtils.dom.click(form.$(".o_selection > a"));
        assert.isNotVisible(form.$(".dropdown-menu.state"));

        form.destroy();
    });

    QUnit.skip("StateSelectionField for list view with hide_label option", async function (assert) {
        assert.expect(6);

        Object.assign(this.data.partner.fields, {
            graph_type: {
                string: "Graph Type",
                type: "selection",
                selection: [
                    ["line", "Line"],
                    ["bar", "Bar"],
                ],
            },
        });
        this.data.partner.records[0].graph_type = "bar";
        this.data.partner.records[1].graph_type = "line";

        const list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: `
                <tree>
                    <field name="graph_type" widget="state_selection" options="{'hide_label': True}"/>
                    <field name="selection" widget="state_selection"/>
                </tree>`,
        });

        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status",
            10,
            "should have ten status selection widgets"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection[name=selection] > span.align-middle",
            5,
            "should have five label on selection widgets"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_selection[name=selection] > span.align-middle:contains(Done)",
            "should have one Done status label"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection[name=selection] > span.align-middle:contains(Normal)",
            3,
            "should have three Normal status label"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection[name=graph_type] > a span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_selection[name=graph_type] > span.align-middle",
            "should not have status label in selection widgets"
        );

        list.destroy();
    });

    QUnit.skip("StateSelectionField in editable list view", async function (assert) {
        assert.expect(33);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                '<field name="foo"/>' +
                '<field name="selection" widget="state_selection"/>' +
                "</tree>",
        });

        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_red",
            "should have one red status"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_green",
            "should have one green status"
        );
        assert.containsNone(list, ".dropdown-menu.state:visible", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        var $cell = list.$("tbody td.o_state_selection_cell").first();
        await testUtils.dom.click(
            list.$(".o_state_selection_cell .o_selection > a span.o_status").first()
        );
        assert.doesNotHaveClass(
            $cell.parent(),
            "o_selected_row",
            "should not be in edit mode since we clicked on the state selection widget"
        );
        assert.containsOnce(list, ".dropdown-menu.state:visible", "there should be a dropdown");
        assert.containsN(
            list,
            ".dropdown-menu.state:visible .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the first option, "Normal"
        await testUtils.dom.click(list.$(".dropdown-menu.state:visible .dropdown-item").first());
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_red",
            "should now have no red status"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_green",
            "should still have one green status"
        );
        assert.containsNone(list, ".dropdown-menu.state:visible", "there should not be a dropdown");
        assert.containsNone(list, "tr.o_selected_row", "should not be in edit mode");

        // switch to edit mode and check the result
        $cell = list.$("tbody td.o_state_selection_cell").first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(), "o_selected_row", "should now be in edit mode");
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_red",
            "should now have no red status"
        );
        assert.containsOnce(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_green",
            "should still have one green status"
        );
        assert.containsNone(list, ".dropdown-menu.state:visible", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await testUtils.dom.click(
            list.$(".o_state_selection_cell .o_selection > a span.o_status").first()
        );
        assert.containsOnce(list, ".dropdown-menu.state:visible", "there should be a dropdown");
        assert.containsN(
            list,
            ".dropdown-menu.state:visible .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on another row
        var $lastCell = list.$("tbody td.o_state_selection_cell").last();
        await testUtils.dom.click($lastCell);
        assert.containsNone(
            list,
            ".dropdown-menu.state:visible",
            "there should not be a dropdown anymore"
        );
        var $firstCell = list.$("tbody td.o_state_selection_cell").first();
        assert.doesNotHaveClass(
            $firstCell.parent(),
            "o_selected_row",
            "first row should not be in edit mode anymore"
        );
        assert.hasClass($lastCell.parent(), "o_selected_row", "last row should be in edit mode");

        // Click on the last status button to make the dropdown appear
        await testUtils.dom.click(
            list.$(".o_state_selection_cell .o_selection > a span.o_status").last()
        );
        assert.containsOnce(list, ".dropdown-menu.state:visible", "there should be a dropdown");
        assert.containsN(
            list,
            ".dropdown-menu.state:visible .dropdown-item",
            2,
            "there should be two options in the dropdown"
        );

        // Click on the last option, "Done"
        await testUtils.dom.click(list.$(".dropdown-menu.state:visible .dropdown-item").last());
        assert.containsNone(
            list,
            ".dropdown-menu.state:visible",
            "there should not be a dropdown anymore"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_red",
            "should still have no red status"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_green",
            2,
            "should now have two green status"
        );
        assert.containsNone(list, ".dropdown-menu.state:visible", "there should not be a dropdown");

        // save
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsNone(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_red",
            "should have no red status"
        );
        assert.containsN(
            list,
            ".o_state_selection_cell .o_selection > a span.o_status.o_status_green",
            2,
            "should have two green status"
        );
        assert.containsNone(list, ".dropdown-menu.state:visible", "there should not be a dropdown");

        list.destroy();
    });

    QUnit.skip(
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
            const serverData = { models: this.data, views };
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
