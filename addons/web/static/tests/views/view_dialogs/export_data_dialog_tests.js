/** @odoo-module */

import {
    click,
    dragAndDrop,
    editInput,
    editSelect,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    mockDownload,
    nextTick,
    triggerEvent,
    mockTimeout,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
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
                    },
                    records: [
                        { id: 1, foo: "blip", display_name: "blipblip", bar: true },
                        { id: 2, foo: "ta tata ta ta", display_name: "macgyver", bar: false },
                        { id: 3, foo: "piou piou", display_name: "Jack O'Neill", bar: true },
                    ],
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
        setupViewRegistries();

        function hasGroup(group) {
            return group === "base.group_allow_export";
        }
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

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
                    required: true,
                    string: "Foo",
                    value: "foo",
                },
                {
                    children: false,
                    field_type: "boolean",
                    id: "bar",
                    relation_field: null,
                    required: false,
                    string: "Bar",
                    value: "bar",
                },
            ],
            activity_ids: [
                {
                    field_type: "one2many",
                    string: "Attendants",
                    required: false,
                    value: "activity_ids/id",
                    id: "activity_ids/partner_ids",
                    params: {
                        model: "mail.activity",
                        prefix: "partner_ids",
                        name: "Company",
                    },
                    children: true,
                },
                {
                    field_type: "one2many",
                    string: "Activity types",
                    required: false,
                    value: "activity_ids/id",
                    id: "activity_ids/types",
                    params: {
                        model: "mail.activity",
                        prefix: "activity_types",
                        name: "Activity types",
                    },
                    children: true,
                },
                {
                    id: "activity_ids/mail_template_ids",
                    string: "Activities/Email templates",
                    value: "activity_ids/mail_template_ids/id",
                    children: true,
                    field_type: "many2many",
                    required: false,
                    relation_field: null,
                    default_export: false,
                    params: {
                        model: "mail.template",
                        prefix: "activity_ids/mail_template_ids",
                        name: "Activities/Email templates",
                    },
                },
            ],
            partner_ids: [
                {
                    children: false,
                    field_type: "many2one",
                    id: "activity_ids/partner_ids/company_ids",
                    relation_field: null,
                    string: "Company",
                    value: "company_ids",
                },
                {
                    children: false,
                    field_type: "char",
                    id: "activity_ids/partner_ids/name",
                    relation_field: null,
                    string: "Partner name",
                    value: "partner_name",
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
            3,
            "There should be only three items visible"
        );

        await editInput(target.querySelector(".modal .o_export_search_input"), null, "ac");
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
        assert.strictEqual(
            target.querySelector(".o_export_search_input").value,
            "ac",
            "search input still contains the search string"
        );

        // Since we use an input of type search, we can't click on the 'X' in tests to reset the value
        await editInput(target.querySelector(".modal .o_export_search_input"), null, "");
        assert.hasClass(
            target.querySelector(".modal .o_export_tree_item:nth-child(2) .o_tree_column"),
            "fw-bolder",
            "required fields have the right style class"
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
        assert.expect(26);

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
                if (args.method === "search_read") {
                    assert.deepEqual(
                        args.kwargs.domain,
                        [["resource", "=", "partner"]],
                        "rpc contains the right domain filter to fetch templates"
                    );
                    return Promise.resolve([{ id: 1, name: "Activities template" }]);
                }
                if (route === "/web/export/namelist") {
                    if (args.export_id === 1) {
                        return Promise.resolve([{ name: "activity_ids", label: "Activities" }]);
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
        assert.containsNone(target, ".o_save_list_btn", "save button is not visible");
        assert.containsOnce(target, ".o_cancel_list_btn .fa-undo", "undo button is visible");
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
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Activities", "Foo", "Bar"]
        );

        await editSelect(target, ".o_exported_lists_select", "");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Activities", "Foo", "Bar"],
            "unselecting an export template has not changed the export list"
        );
        assert.containsNone(
            target,
            ".o_delete_exported_list",
            "trash icon is not visible when no template has been selected"
        );

        await editSelect(target, ".o_exported_lists_select", "2");
        assert.strictEqual(
            target.querySelector(".o_exported_lists_select").selectedOptions[0].textContent,
            "Export template",
            "template name is displayed correctly"
        );

        await click(target, ".o_delete_exported_list");
        assert.strictEqual(
            document.querySelectorAll(".o_dialog .modal-body")[1].textContent,
            "Do you really want to delete this export template?"
        );
        assert.containsN(
            document.body,
            ".o_dialog",
            2,
            "a confirmation dialog has appeared on top"
        );

        await click(document.body, ".o_dialog:nth-child(2) .btn-primary");
        assert.strictEqual(
            target.querySelector(".o_exported_lists_select").selectedOptions[0].textContent,
            "",
            "the template list has been resetted"
        );
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Foo"]
        );
    });

    QUnit.test(
        "Export dialog: interacting with export templates in debug",
        async function (assert) {
            assert.expect(3);

            patchWithCleanup(odoo, { debug: "1" });
            await makeView({
                serverData,
                type: "list",
                resModel: "partner",
                arch: `
                <tree export_xlsx="1"><field name="foo"/></tree>`,
                actionMenus: {},
                mockRPC(route, args) {
                    if (args.method === "search_read") {
                        return Promise.resolve([{ id: 1, name: "Activities template" }]);
                    }
                    if (route === "/web/export/namelist") {
                        if (args.export_id === 1) {
                            return Promise.resolve([{ name: "activity_ids", label: "Activities" }]);
                        }
                        return Promise.resolve([]);
                    }
                    if (route === "/web/export/formats") {
                        return Promise.resolve([{ tag: "csv", label: "CSV" }]);
                    }
                    if (route === "/web/export/get_fields") {
                        return Promise.resolve(fetchedFields.root);
                    }
                },
            });

            await openExportDataDialog();
            assert.strictEqual(
                target.querySelector(".o_fields_list .o_export_field").textContent,
                "Foo (foo)"
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
                "Activities (activity_ids)"
            );
        }
    );

    QUnit.test("Export dialog: interacting with available fields", async function (assert) {
        assert.expect(9);

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
                    if (!args.parent_field) {
                        return Promise.resolve(fetchedFields.root);
                    }
                    if (args.prefix === "partner_ids") {
                        assert.step("fetch fields for 'partner_ids'");
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();

        const firstField = target.querySelector(
            ".o_left_field_panel .o_export_tree_item:first-child"
        );
        await click(firstField);

        // show then hide content for the 'partner_ids' field. Then show it again
        await click(firstField.querySelector(".o_export_tree_item"));
        await click(firstField.querySelector(".o_export_tree_item"));
        await click(firstField.querySelector(".o_export_tree_item"));
        assert.verifySteps(
            ["fetch fields for 'partner_ids'"],
            "we should only make one rpc to fetch fields"
        );

        assert.containsNone(
            firstField.querySelector(
                ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']",
                ".o_expand_parent",
                "available fields are limited to 2 levels of subfields"
            )
        );

        await triggerEvent(
            target,
            ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']",
            "dblclick"
        );
        assert.hasClass(
            firstField.querySelector(
                ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids'] .o_add_field"
            ),
            "o_inactive",
            "field has been added by double clicking on it and cannot be added anymore"
        );

        await click(firstField.querySelector(".o_add_field"));
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Foo", "Company", "Activities"]
        );
        await triggerEvent(target, ".o_export_tree_item[data-field_id='activity_ids']", "dblclick");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Foo", "Company", "Activities"],
            "double clicking on an expandable field does not add the field"
        );

        await dragAndDrop(".o_export_field:first-child", ".o_export_field:nth-child(2)");
        await dragAndDrop(".o_export_field:nth-child(3)", ".o_export_field:first-child");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Activities", "Company", "Foo"]
        );

        await click(target.querySelector(".o_export_field:nth-child(2) .o_remove_field"));
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Activities", "Foo"]
        );

        await click(
            firstField.querySelector(
                ".o_export_tree_item[data-field_id='activity_ids/partner_ids/name'] .o_add_field"
            )
        );
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_right_field_panel .o_export_field")),
            ["Activities", "Foo", "Partner name"]
        );
    });

    QUnit.test("Export dialog: compatible and export type options", async function (assert) {
        assert.expect(5);

        mockDownload(({ url, data }) => {
            assert.strictEqual(url, "/web/export/wow", "should call get_file with the correct url");
            assert.ok(
                JSON.parse(data.data)["import_compat"],
                "request to generate the file must have 'import_compat' as true"
            );
            return Promise.resolve();
        });

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
                        { tag: "wow", label: "WOW" },
                    ]);
                }
                if (route === "/web/export/get_fields") {
                    if (!args.parent_field) {
                        return Promise.resolve(fetchedFields.root);
                    }
                    if (args.prefix === "partner_ids") {
                        assert.step("fetch fields for 'partner_ids'");
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();

        assert.containsN(
            target,
            "input[name='o_export_format_name']",
            3,
            "three inputs are available to choose the format"
        );
        assert.strictEqual(
            target.querySelectorAll("input[name='o_export_format_name']")[2].value,
            "wow",
            "the third input has the right value"
        );
        assert.strictEqual(
            target.querySelectorAll("input[name='o_export_format_name']")[2].labels[0].textContent,
            "WOW",
            "the third input has the right label"
        );

        await click(target.querySelectorAll("input[name='o_export_format_name']")[2]);
        await click(target, ".o_import_compat input");
        await click(target, ".o_select_button");
    });

    QUnit.test("Export dialog: many2many fields are extendable", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree><field name="foo"/></tree>',
            actionMenus: {},
            mockRPC(route, args) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([
                        { tag: "csv", label: "CSV" },
                        { tag: "xls", label: "Excel" },
                    ]);
                }
                if (route === "/web/export/get_fields") {
                    if (!args.parent_field) {
                        return Promise.resolve(fetchedFields.root);
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();
        await click(target, "[data-field_id='activity_ids']");
        assert.hasClass(
            target.querySelector("[data-field_id='activity_ids/mail_template_ids'] span"),
            "o_expand_parent",
            "many2many element is expandable"
        );
    });

    QUnit.test("Export dialog: export list with 'exportable: false'", async function (assert) {
        serverData.models.partner.fields.not_exportable = {
            string: "Not exportable",
            type: "char",
            exportable: false,
        };
        serverData.models.partner.fields.exportable = { string: "Exportable", type: "char" };

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `<tree export_xlsx="1">
                <field name="foo"/>
                <field name="not_exportable"/>
                <field name="exportable"/>
            </tree>`,
            actionMenus: {},
            mockRPC(route, args) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([{ tag: "csv", label: "CSV" }]);
                }
                if (route === "/web/export/get_fields") {
                    if (!args.parent_field) {
                        return Promise.resolve([
                            ...fetchedFields.root,
                            {
                                id: "not_exportable",
                                string: "Not exportable",
                                type: "char",
                                exportable: false,
                            },
                            {
                                id: "exportable",
                                string: "Exportable",
                            },
                        ]);
                    }
                    if (args.prefix === "partner_ids") {
                        assert.step("fetch fields for 'partner_ids'");
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();
        assert.containsN(target, ".o_export_field", 2, "only two fields are selected in the list");
        assert.strictEqual(
            target.querySelector(".o_fields_list").textContent,
            "FooExportable",
            "values are the correct ones"
        );
    });

    QUnit.test("Export dialog: display on small screen after resize", async function (assert) {
        const { execRegisteredTimeouts } = mockTimeout();
        const ui = {
            activateElement: () => {},
            deactivateElement: () => {},
            size: 4,
        };
        const fakeUIService = {
            start(env) {
                Object.defineProperty(env, "isSmall", {
                    get() {
                        return ui.size === 2;
                    },
                });
                return ui;
            },
        };

        serviceRegistry.add("ui", fakeUIService);

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
                        { tag: "wow", label: "WOW" },
                    ]);
                }
                if (route === "/web/export/get_fields") {
                    if (!args.parent_field) {
                        return Promise.resolve(fetchedFields.root);
                    }
                    if (args.prefix === "partner_ids") {
                        assert.step("fetch fields for 'partner_ids'");
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();

        await click(target.querySelector(".modal .o_export_tree_item .o_add_field"));

        ui.size = 2;
        window.dispatchEvent(new Event("resize"));
        execRegisteredTimeouts();

        await nextTick();
        assert.containsNone(
            target,
            ".o_export_field_sortable",
            "exported fields can't be sorted by drag and drop"
        );

        ui.size = 4;
        window.dispatchEvent(new Event("resize"));
        execRegisteredTimeouts();

        await nextTick();
        assert.containsN(
            target,
            ".o_export_field_sortable",
            2,
            "exported fields can't be sorted by drag and drop"
        );
    });

    QUnit.test("ExportDialog: export all records of the domain", async function (assert) {
        assert.expect(2);
        let isDomainSelected = false;

        mockDownload(({ data }) => {
            if (isDomainSelected) {
                assert.deepEqual(
                    JSON.parse(data.data),
                    {
                        context: { lang: "en", uid: 7, tz: "taht" },
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
                                type: "boolean",
                            },
                        ],
                    },
                    "should be called with correct params when all records are selected"
                );
            } else {
                assert.deepEqual(
                    JSON.parse(data.data),
                    {
                        context: { lang: "en", uid: 7, tz: "taht" },
                        model: "partner",
                        domain: [["bar", "!=", "glou"]],
                        groupby: [],
                        ids: [1],
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
                                type: "boolean",
                            },
                        ],
                    },
                    "should be called with correct params when only one record is selected"
                );
            }
            return Promise.resolve();
        });

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree export_xlsx="1" limit="1">
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            actionMenus: {},
            domain: [["bar", "!=", "glou"]],
            mockRPC(route) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([{ tag: "xls", label: "Excel" }]);
                }
                if (route === "/web/export/get_fields") {
                    return Promise.resolve(fetchedFields.root);
                }
            },
        });

        await openExportDataDialog();
        await click(target.querySelector(".o_select_button"));
        await click(target.querySelector(".btn-close"));

        isDomainSelected = true;
        await click(target.querySelector(".o_list_select_domain"));
        await click(target.querySelector(".o_control_panel .o_cp_action_menus .dropdown-toggle"));
        await click(
            target.querySelector(
                ".o_control_panel .o_cp_action_menus .dropdown-menu span:first-child"
            )
        );
        await click(target.querySelector(".o_select_button"));
    });

    QUnit.test("Direct export list", async function (assert) {
        assert.expect(2);

        mockDownload(({ url, data }) => {
            assert.strictEqual(
                url,
                "/web/export/xlsx",
                "should call get_file with the correct url"
            );
            assert.deepEqual(
                JSON.parse(data.data),
                {
                    context: { lang: "en", uid: 7, tz: "taht" },
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
                            type: "boolean",
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
        });

        await click(target.querySelector(".o_list_export_xlsx"));
    });

    QUnit.test("Direct export grouped list ", async function (assert) {
        assert.expect(2);

        mockDownload(({ url, data }) => {
            assert.strictEqual(
                url,
                "/web/export/xlsx",
                "should call get_file with the correct url"
            );
            assert.deepEqual(
                JSON.parse(data.data),
                {
                    context: { lang: "en", uid: 7, tz: "taht" },
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
                            type: "boolean",
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
        });

        await click(target.querySelector(".o_list_export_xlsx"));
    });

    QUnit.test("Export dialog with duplicated fields", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree>
                    <field name="foo" string="Foo"/>
                    <field name="foo" string="duplicate of Foo"/>
                </tree>`,
            actionMenus: {},
            mockRPC(route) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([{ tag: "csv", label: "CSV" }]);
                }
                if (route === "/web/export/get_fields") {
                    return Promise.resolve(fetchedFields.root);
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_list_table th:nth-child(2)").textContent,
            "Foo",
            "first column contains the field"
        );
        assert.strictEqual(
            target.querySelector(".o_list_table th:nth-child(3)").textContent,
            "duplicate of Foo",
            "second column contains the duplicated field"
        );

        await openExportDataDialog();
        assert.containsOnce(
            target,
            ".modal .o_export_field",
            "there is only one field in export field list."
        );
        assert.strictEqual(
            target.querySelector(".modal .o_export_field").textContent,
            "Foo",
            "the field to export corresponds to the field displayed in the list view"
        );
    });

    QUnit.test(
        "Export dialog: export list contains field with 'default_export: true'",
        async function (assert) {
            await makeView({
                serverData,
                type: "list",
                resModel: "partner",
                arch: `<tree export_xlsx="1">
                <field name="foo"/>
            </tree>`,
                actionMenus: {},
                mockRPC(route, args) {
                    if (route === "/web/export/formats") {
                        return Promise.resolve([{ tag: "csv", label: "CSV" }]);
                    }
                    if (route === "/web/export/get_fields") {
                        if (!args.parent_field) {
                            return Promise.resolve([
                                ...fetchedFields.root,
                                {
                                    id: "default_exportable",
                                    string: "Default exportable",
                                    type: "char",
                                    default_export: true,
                                },
                            ]);
                        }
                        return Promise.resolve(fetchedFields[args.prefix]);
                    }
                },
            });

            await openExportDataDialog();
            assert.containsN(target, ".o_export_field", 2, "two fields are selected in the list");
            assert.strictEqual(
                target.querySelector(".o_fields_list").textContent,
                "FooDefault exportable",
                "values are the correct ones"
            );
        }
    );

    QUnit.test("Export dialog: search subfields", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree export_xlsx="1"><field name="foo"/></tree>`,
            actionMenus: {},
            mockRPC(route, args) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([{ tag: "csv", label: "CSV" }]);
                }
                if (route === "/web/export/get_fields") {
                    if (!args.parent_field) {
                        return Promise.resolve(fetchedFields.root);
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();

        const firstField = target.querySelector(
            ".o_left_field_panel .o_export_tree_item:first-child"
        );
        await click(firstField);

        // show then hide content for the 'partner_ids' field.
        // this will load subfields and make them available to search
        await click(firstField.querySelector(".o_export_tree_item"));
        await click(firstField.querySelector(".o_export_tree_item"));
        await editInput(target, ".o_export_search_input", "company");
        assert.containsOnce(
            target,
            ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']",
            "subfield that was known has been found and is displayed"
        );
    });

    QUnit.test("Export dialog: expand subfields after search", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree export_xlsx="1"><field name="foo"/></tree>`,
            actionMenus: {},
            mockRPC(route, args) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([{ tag: "csv", label: "CSV" }]);
                }
                if (route === "/web/export/get_fields") {
                    if (!args.parent_field) {
                        return Promise.resolve(fetchedFields.root);
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();

        const firstField = target.querySelector(
            ".o_left_field_panel .o_export_tree_item:first-child"
        );
        // show then hide content for the 'activity_ids' field.
        // this will load subfields and make them available to search
        await click(firstField);
        await click(firstField);
        await editInput(target, ".o_export_search_input", "Attendants");
        assert.containsOnce(
            target,
            ".o_export_tree_item[data-field_id='activity_ids/partner_ids']",
            "subfield that was known has been found and is displayed"
        );

        await click(
            target.querySelector(".o_export_tree_item[data-field_id='activity_ids/partner_ids']")
        );
        await nextTick();
        // 'Company' should be shown even if the company_ids string doesn't match the search string
        // since the toggle was done by the user to show subfields
        assert.containsOnce(
            target,
            ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']",
            "subfield has been loaded and is displayed"
        );
    });

    QUnit.test("Export dialog: search in debug", async function (assert) {
        patchWithCleanup(odoo, { debug: "1" });

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree export_xlsx="1"><field name="foo"/></tree>`,
            actionMenus: {},
            mockRPC(route, args) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([{ tag: "csv", label: "CSV" }]);
                }
                if (route === "/web/export/get_fields") {
                    if (!args.parent_field) {
                        return Promise.resolve(fetchedFields.root);
                    }
                    return Promise.resolve(fetchedFields[args.prefix]);
                }
            },
        });

        await openExportDataDialog();

        await click(target.querySelector(".o_left_field_panel .o_export_tree_item:first-child"));
        await click(target.querySelector(".o_export_tree_item:first-child .o_export_tree_item"));
        await editInput(target, ".o_export_search_input", "company_ids");
        assert.containsOnce(
            target,
            ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']",
            "subfield has been found with its technical name and is displayed"
        );
    });

    QUnit.test(
        "Direct export list take optional fields into account",
        async function (assert) {
            assert.expect(3);

            mockDownload(({ url, data }) => {
                assert.strictEqual(
                    url,
                    "/web/export/xlsx",
                    "should call get_file with the correct url"
                );
                assert.deepEqual(JSON.parse(data.data).fields, [
                    { label: "Bar", name: "bar", type: "boolean" },
                ]);
                return Promise.resolve();
            });

            await makeView({
                serverData,
                type: "list",
                resModel: "partner",
                arch: `
                 <tree>
                     <field name="foo" optional="show"/>
                     <field name="bar" optional="show"/>
                 </tree>`,
            });

            await click(target, "table .o_optional_columns_dropdown .dropdown-toggle");
            await click(target, "div.o_optional_columns_dropdown span.dropdown-item:first-child");
            assert.containsN(
                target,
                "th",
                3,
                "should have 3 th, 1 for selector, 1 for columns, 1 for optional columns"
            );

            await click(target.querySelector(".o_list_export_xlsx"));
        }
    );

    QUnit.test("Export dialog: disable button during export", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `
                <tree><field name="foo"/></tree>`,
            actionMenus: {},
            mockRPC(route, args) {
                if (route === "/web/export/formats") {
                    return Promise.resolve([{ tag: "xls", label: "Excel" }]);
                }
                if (route === "/web/export/get_fields") {
                    return Promise.resolve(fetchedFields.root);
                }
            },
        });
        const def = makeDeferred();
        mockDownload(() => def);

        await openExportDataDialog();

        const exportButton = target.querySelector(".o_select_button");
        assert.notOk(exportButton.disabled, "export button is clickable before the first click");

        await click(exportButton);
        assert.ok(exportButton.disabled, "export button is disabled during export");

        def.resolve();
        await nextTick();

        assert.notOk(exportButton.disabled, "export button is enabled after export");
    });
});
