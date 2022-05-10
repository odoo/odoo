/** @odoo-module */

import {
    click,
    editInput,
    editSelect,
    getFixture,
    mockDownload,
    nextTick,
} from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { makeFakeUserService } from "../../helpers/mock_services";

const serviceRegistry = registry.category("services");

QUnit.module("ViewDialogs", (hooks) => {
    let serverData;
    let target;
    let fetchedFields;

    const openExportDataDialog = async () => {
        await click(target.querySelector(".o_list_record_selector input[type='checkbox'"));
        await click(target.querySelector(".o_control_panel .o_cp_action_menus .dropdown-toggle"));
        await click(
            target.querySelector(
                ".o_control_panel .o_cp_action_menus .dropdown-menu span:first-child"
            )
        );
        await nextTick();
    };

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
                        export_fields: {
                            string: "Templates fields",
                            type: "one2many",
                            relation: "partner",
                        },
                    },
                    records: [],
                },
            },
        };
        target = getFixture();
        setupControlPanelServiceRegistry();

        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
        serviceRegistry.add("dialog", dialogService);

        fetchedFields = {
            root: [
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
            ],
            activity_ids: [
                {
                    field_type: "one2many",
                    string: "Attendants",
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
            ],
        };
    });

    QUnit.module("ExportDataDialog");

    QUnit.test("Export dialog UI test", async function (assert) {
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
                    return Promise.resolve(fetchedFields.root);
                }
            },
        });

        await openExportDataDialog();

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

    QUnit.test("Export dialog: interacting with export templates", async function (assert) {
        assert.expect(17);

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree export_xlsx="1"><field name="foo"/></tree>`,
            actionMenus: {},
            mockRPC(route, args) {
                if (args.method === "create") {
                    assert.strictEqual(args.model, "ir.exports");
                    assert.strictEqual(
                        args.args[0].name,
                        "Export template",
                        "the template name is correctly sent"
                    );
                    return 2;
                }
                if (route === "/web/dataset/call_kw") {
                    return Promise.resolve([{ id: 1, name: "Activities template" }]);
                }
                if (route === "/web/export/namelist") {
                    if (args.export_id === 1) {
                        return Promise.resolve([{ name: "activity_ids" }]);
                    }
                    return Promise.resolve([]);
                }
                if (route === "/web/export/formats") {
                    return Promise.resolve([
                        { tag: "csv", label: "CSV" },
                        { tag: "xls", label: "Excel" },
                    ]);
                }
                if (route === "/web/export/get_fields") {
                    return Promise.resolve([
                        ...fetchedFields.root,
                        {
                            children: false,
                            field_type: "string",
                            id: "third_field",
                            relation_field: null,
                            required: false,
                            string: "Third field selected",
                            value: "third_field",
                        },
                    ]);
                }
            },
        });

        await openExportDataDialog();

        assert.containsOnce(target, ".o_dialog", "the export dialog should be visible");
        assert.hasClass(
            target.querySelector(".o_export_tree_item:nth-child(2) .o_add_field"),
            "o_inactive",
            "fields already selected cannot be added anymore"
        );

        // load a template which contains the activity_ids field
        await editSelect(target, ".o_exported_lists_select", "1");
        assert.containsOnce(
            target,
            ".o_fields_list .o_export_field",
            "only one field is present for the selected template"
        );
        assert.strictEqual(
            target.querySelector(".o_fields_list .o_export_field").textContent,
            "Activities"
        );

        // add a new field to the exported fields list allow the edition of the template
        await click(target.querySelector(".o_export_tree_item:nth-child(2) .o_add_field"));
        assert.containsOnce(
            target,
            ".o_exported_lists_select",
            "the template list is still visible"
        );
        assert.containsOnce(target, ".o_save_list_btn", "a save button is now visible");
        assert.containsOnce(target, ".o_cancel_list_btn", "a cancel button is now visible");
        assert.containsN(
            target,
            ".o_fields_list .o_export_field",
            2,
            "the list contains two fields"
        );

        await click(target.querySelector(".o_cancel_list_btn"));
        assert.containsOnce(
            target,
            ".o_fields_list .o_export_field",
            "the template has been reset and the added field is no longer in the list"
        );

        await click(target.querySelector(".o_export_tree_item:nth-child(2) .o_add_field"));
        await editSelect(target, ".o_exported_lists_select", "new_template");
        assert.containsNone(target, ".o_exported_lists_select", "the template list is now hidden");
        assert.containsOnce(
            target,
            "input.o_save_list_name",
            "an input is present to edit the current template"
        );

        await click(target.querySelector(".o_save_list_btn"));
        assert.strictEqual(
            target.querySelector(".o_notification").textContent,
            "Please enter save field list name",
            "should display a notification if the template list has no name"
        );

        await editInput(target, ".o_save_list_name", "Export template");
        await click(target.querySelector(".o_cancel_list_btn"));
        assert.containsOnce(target, ".o_exported_lists_select", "the template list is now visible");

        await click(target.querySelector(".o_export_tree_item:nth-child(3) .o_add_field"));
        assert.containsN(
            target,
            ".o_fields_list .o_export_field",
            3,
            "three fields are present in the exported fields list"
        );
        await editSelect(target, ".o_exported_lists_select", "new_template");
        await editInput(target, ".o_save_list_name", "Export template");
        await click(target.querySelector(".o_save_list_btn"));

        assert.strictEqual(
            target.querySelector(".o_exported_lists_select").selectedOptions[0].textContent,
            "Export template",
            "the new template is now selected"
        );
    });

    QUnit.skipWOWL("Export dialog: interacting with available fields", async function (assert) {
        //assert.expect(17);

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree export_xlsx="1"><field name="foo"/></tree>`,
            actionMenus: {},
            mockRPC(route, args) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([
                        { tag: "csv", label: "CSV" },
                        { tag: "xls", label: "Excel" },
                    ]);
                }
                if (route === "/web/export/get_fields") {
                    console.log(args);
                    return Promise.resolve(fetchedFields.root);
                }
            },
        });

        await openExportDataDialog();

        // TODO...
    });

    QUnit.skipWOWL("Direct export list", async function (assert) {
        assert.expect(2);

        mockDownload(({ data, url }) => {
            assert.strictEqual(
                url,
                "/web/export/xlsx",
                "should call get_file with the correct url"
            );
            assert.deepEqual(
                JSON.parse(data.data),
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
            return Promise.resolve();
        });

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
            mockRPC(route) {
                if (route === "/web/export/get_fields") {
                    return Promise.resolve(fetchedFields.root);
                }
            },
        });

        await click(target.querySelector(".o_list_export_xlsx"));
    });

    QUnit.skipWOWL("Direct export grouped list ", async function (assert) {
        assert.expect(2);

        mockDownload(({ data, url }) => {
            assert.strictEqual(
                url,
                "/web/export/xlsx",
                "should call get_file with the correct url"
            );
            assert.deepEqual(
                JSON.parse(data.data),
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
            return Promise.resolve();
        });

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
            mockRPC(route) {
                if (route === "/web/export/get_fields") {
                    return Promise.resolve(fetchedFields.root);
                }
            },
        });

        await click(target.querySelector(".o_list_export_xlsx"));
    });
});
