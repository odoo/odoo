/** @odoo-module */

import { click, editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { makeFakeUserService } from "../../helpers/mock_services";

const serviceRegistry = registry.category("services");

QUnit.module("ViewDialogs", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(async () => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        instrument: {
                            string: "Instruments",
                            type: "many2one",
                            relation: "instrument",
                        },
                    },
                    records: [
                        { id: 1, foo: "blip", display_name: "blipblip", bar: true },
                        { id: 2, foo: "ta tata ta ta", display_name: "macgyver", bar: false },
                        { id: 3, foo: "piou piou", display_name: "Jack O'Neill", bar: true },
                    ],
                },
                instrument: {
                    fields: {
                        name: { string: "name", type: "char" },
                        badassery: {
                            string: "level",
                            type: "many2many",
                            relation: "badassery",
                            domain: [["level", "=", "Awsome"]],
                        },
                    },
                },

                badassery: {
                    fields: {
                        level: { string: "level", type: "char" },
                    },
                    records: [{ id: 1, level: "Awsome" }],
                },

                product: {
                    fields: {
                        name: { string: "name", type: "char" },
                        partner: { string: "Doors", type: "one2many", relation: "partner" },
                    },
                    records: [{ id: 1, name: "The end" }],
                },
                "ir.exports": {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
            },
        };
        target = getFixture();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
    });

    QUnit.module("ExportDataDialog");

    QUnit.test("Export dialog UI test", async function (assert) {
        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree><field name="foo"/></tree>',
            actionMenus: {},
            mockRPC(route) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([
                        { tag: "csv", label: "CSV" },
                        { tag: "xls", label: "Excel" },
                    ]);
                }
                if (route === "/web/export/get_fields") {
                    return Promise.resolve([
                        {
                            field_type: "one2many",
                            string: "Activities",
                            required: false,
                            value: "activity_ids/id",
                            id: "activity_ids",
                            params: {
                                model: "mail.activity",
                                prefix: "activity_ids",
                                name: "Activities",
                            },
                            relation_field: "res_id",
                            children: true,
                        },
                        {
                            children: false,
                            field_type: "char",
                            id: "foo",
                            relation_field: null,
                            required: false,
                            string: "Foo",
                            value: "foo",
                        },
                    ]);
                }
            },
        });

        // Open the export modal
        await click(target.querySelector("thead th.o_list_record_selector input"));
        await click(target.querySelector(".o_control_panel .o_cp_action_menus .dropdown-toggle"));
        await click(
            target.querySelector(
                ".o_control_panel .o_cp_action_menus .dropdown-menu span:first-child"
            )
        );

        assert.containsOnce(target, ".o_dialog", "the export dialog should be visible");
        assert.containsN(
            target,
            ".o_dialog .o_export_tree_item",
            2,
            "There should be only two items visible"
        );
        await editInput(target.querySelector(".modal .o_export_search_input"), null, "a");
        assert.containsOnce(target, ".modal .o_export_tree_item", "Only match item visible");
        // Add field
        await click(target.querySelector(".modal .o_export_tree_item .o_add_field"));
        assert.containsN(
            target,
            ".modal .o_export_field",
            2,
            "There should be two fields in export field list."
        );
        assert.strictEqual(
            target.querySelector(".modal .o_export_field:nth-child(2)").textContent,
            "Activities",
            "string of second field in export list should be 'Activities'"
        );
        // Remove field
        await click(target, ".modal .o_export_field:first-child .o_remove_field");
        assert.containsOnce(
            target,
            ".modal .o_export_field",
            "There should be only one field in list"
        );
    });

    QUnit.skipWOWL("Export dialog from list view", async function (assert) {
        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        assert.containsOnce(target, "div.o_control_panel .o_cp_buttons .o_list_export_xlsx");
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            actionMenus: {},
            arch: `
                <tree export_xlsx="1">
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            domain: [["bar", "!=", "glou"]],
            // session: {
            //     ...this.mockSession,
            //     get_file(args) {
            //         let data = JSON.parse(args.data.data);
            //         assert.strictEqual(args.url, '/web/export/xlsx', "should call get_file with the correct url");
            //         assert.deepEqual(data, {
            //             context: {},
            //             model: 'partner',
            //             domain: [['bar', '!=', 'glou']],
            //             groupby: [],
            //             ids: false,
            //             import_compat: false,
            //             fields: [{
            //                 name: 'foo',
            //                 label: 'Foo',
            //                 type: 'char',
            //             }, {
            //                 name: 'bar',
            //                 label: 'Bar',
            //                 type: 'char',
            //             }]
            //         }, "should be called with correct params");
            //         args.complete();
            //     },
            // },
        });

        // Open the export dialog
        await click(target.querySelector(".o_list_record_selector input[type='checkbox'"));
        await click(target.querySelector(".o_control_panel .o_cp_action_menus .dropdown-toggle"));
        await click(
            target.querySelector(
                ".o_control_panel .o_cp_action_menus .dropdown-menu span:first-child"
            )
        );

        assert.containsOnce(target, ".o_dialog", "the export dialog should be visible");
        assert.ok(false);
    });

    QUnit.skipWOWL("Direct export list", async function (assert) {
        assert.expect(2);

        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        assert.containsOnce(target, "div.o_control_panel .o_cp_buttons .o_list_export_xlsx");
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            actionMenus: {},
            arch: `
                <tree export_xlsx="1">
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            domain: [["bar", "!=", "glou"]],
            session: {
                ...this.mockSession,
                get_file(args) {
                    let data = JSON.parse(args.data.data);
                    assert.strictEqual(
                        args.url,
                        "/web/export/xlsx",
                        "should call get_file with the correct url"
                    );
                    assert.deepEqual(
                        data,
                        {
                            context: {},
                            model: "partner",
                            domain: [["bar", "!=", "glou"]],
                            groupby: [],
                            ids: false,
                            import_compat: false,
                            fields: [
                                {
                                    name: "foo",
                                    label: "Foo",
                                    type: "char",
                                },
                                {
                                    name: "bar",
                                    label: "Bar",
                                    type: "char",
                                },
                            ],
                        },
                        "should be called with correct params"
                    );
                    args.complete();
                },
            },
        });

        await click(target.querySelector(".o_list_export_xlsx"));
    });

    QUnit.skipWOWL("Direct export grouped list ", async function (assert) {
        assert.expect(2);

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            groupBy: ["foo", "bar"],
            domain: [["bar", "!=", "glou"]],
            session: {
                ...this.mockSession,
                get_file(args) {
                    let data = JSON.parse(args.data.data);
                    assert.strictEqual(
                        args.url,
                        "/web/export/xlsx",
                        "should call get_file with the correct url"
                    );
                    assert.deepEqual(
                        data,
                        {
                            context: {},
                            model: "partner",
                            domain: [["bar", "!=", "glou"]],
                            groupby: ["foo", "bar"],
                            ids: false,
                            import_compat: false,
                            fields: [
                                {
                                    name: "foo",
                                    label: "Foo",
                                    type: "char",
                                },
                                {
                                    name: "bar",
                                    label: "Bar",
                                    type: "char",
                                },
                            ],
                        },
                        "should be called with correct params"
                    );
                    args.complete();
                },
            },
        });

        await click(target.querySelector(".o_list_export_xlsx"));
    });
});
