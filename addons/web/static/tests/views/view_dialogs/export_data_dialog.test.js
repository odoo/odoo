import { expect, test } from "@odoo/hoot";
import {
    check,
    dblclick,
    pointerDown,
    queryAll,
    queryAllTexts,
    queryFirst,
    select,
} from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    getMockEnv,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";

import { download } from "@web/core/network/download";

async function exportAllAction() {
    await contains(".o_cp_action_menus .dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item").click();
}
const openExportDialog = async () => {
    if (getMockEnv().isSmall) {
        await pointerDown(".o_data_row:nth-child(1)");
        await runAllTimers();
    } else {
        await contains(".o_list_record_selector input[type='checkbox']").click();
    }
    await contains(".o_control_panel .o_cp_action_menus .dropdown-toggle").click();
    await contains(".dropdown-menu span:contains(Export)").click();
    await animationFrame();
};

class Partner extends models.Model {
    display_name = fields.Char();
    foo = fields.Char();
    bar = fields.Boolean();

    _records = [
        { id: 1, foo: "blip", display_name: "blipblip", bar: true },
        { id: 2, foo: "ta tata ta ta", display_name: "macgyver", bar: false },
        { id: 3, foo: "piou piou", display_name: "Jack O'Neill", bar: true },
    ];
}
class Users extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}
class IrExports extends models.Model {
    _name = "ir.exports";
    name = fields.Char();
    resource = fields.Char();
    export_fields = fields.One2many({ relation: "ir.exports.line" });
}
class IrExportsLine extends models.Model {
    _name = "ir.exports.line";
    name = fields.Char();
    export_id = fields.Many2one({ relation: "ir.exports" });
}
defineModels([Partner, Users, IrExports, IrExportsLine]);

const fetchedFields = {
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

test("Export dialog UI test", async () => {
    onRpc("/web/export/formats", () => {
        return [
            { tag: "csv", label: "CSV" },
            { tag: "xls", label: "Excel" },
        ];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();
    expect(`.o_dialog`).toHaveCount(1);
    expect(`.o_dialog .o_export_tree_item`).toHaveCount(3, {
        message: "There should be only three items visible",
    });
    await contains(".modal .o_export_search_input").edit("ac");
    expect(`.modal .o_export_tree_item`).toHaveCount(1, {
        message: "Only matching item is visible",
    });
    await contains(".modal .o_export_tree_item .o_add_field").click();
    expect(`.modal .o_export_field`).toHaveCount(2, {
        message: "There should be two fields in export field list",
    });
    expect(".modal .o_export_field:nth-child(2)").toHaveText("Activities");
    expect(".o_export_search_input").toHaveValue("ac", {
        message: "Search input still contains the search string",
    });
    await contains(".modal .o_export_search_input").edit("");
    expect(".modal .o_export_tree_item:nth-child(2) .o_tree_column").toHaveClass("fw-bolder");
    await contains(".modal .o_export_field:first-child .o_remove_field").click();
    expect(`.modal .o_export_field`).toHaveCount(1);
});

test("Export dialog: interacting with export templates", async () => {
    onRpc("/web/export/formats", () => {
        return [
            { tag: "csv", label: "CSV" },
            { tag: "xls", label: "Excel" },
        ];
    });
    onRpc("/web/export/get_fields", () => {
        return [
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
        ];
    });
    onRpc("/web/export/namelist", async (request) => {
        const { params } = await request.json();
        if (params.export_id === 1) {
            return [{ id: "activity_ids", string: "Activities" }];
        }
        return [];
    });
    onRpc(({ args, method, model, kwargs }) => {
        switch (method) {
            case "search_read":
                expect(kwargs.domain).toEqual([["resource", "=", "partner"]], {
                    message: "rpc contains the right domain filter to fetch templates",
                });
                return [{ id: 1, name: "Activities template" }];
            case "create":
                expect(model).toBe("ir.exports");
                expect(args[0][0].name).toBe("Export template", {
                    message: "the template name is correctly sent",
                });
                return [2];
        }
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    expect(`.o_dialog`).toHaveCount(1);
    expect(".o_export_tree_item:nth-child(2) .o_add_field").toHaveClass("o_inactive", {
        message: "fields already selected cannot be added anymore",
    });

    // load a template which contains the activity_ids field
    await select("1", { target: ".o_exported_lists_select" });
    await animationFrame();
    expect(`.o_fields_list .o_export_field`).toHaveCount(1);
    expect(`.o_fields_list .o_export_field`).toHaveText("Activities");
    await contains(".o_export_tree_item:nth-child(2) .o_add_field").click();
    expect(`.o_exported_lists_select`).toHaveCount(1);
    expect(`.o_save_list_btn`).toHaveCount(0);
    expect(`.o_cancel_list_btn .fa-undo`).toHaveCount(1);
    expect(`.o_fields_list .o_export_field`).toHaveCount(2);
    await contains(".o_cancel_list_btn").click();
    expect(`.o_fields_list .o_export_field`).toHaveCount(1, {
        message: "the template has been reset and the added field is no longer in the list",
    });
    await contains(".o_export_tree_item:nth-child(2) .o_add_field").click();
    await select("new_template", { target: ".o_exported_lists_select" });
    await animationFrame();
    expect(`.o_exported_lists_select`).toHaveCount(0);
    expect(`input.o_save_list_name`).toHaveCount(1, {
        message: "an input is present to edit the current template name",
    });
    await contains(".o_save_list_btn").click();
    expect(".o_notification").toHaveText("Please enter save field list name");
    await contains(".o_cancel_list_btn").click();
    expect(`.o_exported_lists_select`).toHaveCount(1);
    await contains(".o_export_tree_item:nth-child(3) .o_add_field").click();
    expect(`.o_fields_list .o_export_field`).toHaveCount(3);
    await select("new_template", { target: ".o_exported_lists_select" });
    await animationFrame();
    await contains(".o_save_list_name").edit("Export template");
    await contains(".o_save_list_btn").click();
    expect(".o_exported_lists_select").toHaveValue("2", {
        message: "the new template is now selected",
    });
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual([
        "Activities",
        "Foo",
        "Bar",
    ]);
    await select("", { target: ".o_exported_lists_select" });
    await animationFrame();
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual(
        ["Activities", "Foo", "Bar"],
        {
            message: "unselecting an export template has not changed the export list",
        }
    );
    expect(".o_delete_exported_list").toHaveCount(0, {
        message: "trash icon is not visible when no template has been selected",
    });
    await select("2", { target: ".o_exported_lists_select" });
    await animationFrame();
    await contains(".o_delete_exported_list").click();
    expect(queryAll(".o_dialog .modal-body")[1]).toHaveText(
        "Do you really want to delete this export template?"
    );
    await contains(".o-overlay-item:nth-child(2) .btn-primary").click();
    expect(".o_exported_lists_select").toHaveValue("", {
        message: "the template list has been reset",
    });
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual(["Foo"]);
});

test("Export dialog: interacting with export templates in debug", async () => {
    serverState.debug = true;

    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", () => {
        return [...fetchedFields.root];
    });
    onRpc("/web/export/namelist", async (request) => {
        const { params } = await request.json();
        if (params.export_id === 1) {
            return [{ id: "activity_ids", string: "Activities" }];
        }
        return [];
    });
    onRpc(({ method }) => {
        if (method === "search_read") {
            return [{ id: 1, name: "Activities template" }];
        }
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    expect(".o_fields_list .o_export_field").toHaveText("Foo (foo)");
    await select("1", { target: ".o_exported_lists_select" });
    await animationFrame();
    expect(".o_fields_list .o_export_field").toHaveCount(1);
    expect(".o_fields_list .o_export_field").toHaveText("Activities (activity_ids)");
});

test.tags("desktop");
test("Export dialog: interacting with available fields", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        if (params.prefix === "partner_ids") {
            expect.step("fetch fields for 'partner_ids'");
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    const firstField = ".o_left_field_panel .o_export_tree_item:first-child ";
    await contains(firstField).click();

    // show then hide content for the 'partner_ids' field. Then show it again
    await contains(firstField + ".o_export_tree_item").click();
    await contains(firstField + ".o_export_tree_item").click();
    await contains(firstField + ".o_export_tree_item").click();
    // we should only make one rpc to fetch fields
    expect.verifySteps(["fetch fields for 'partner_ids'"]);
    expect(
        ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids'] .o_expand_parent"
    ).toHaveCount(0, {
        message: "available fields are limited to 2 levels of subfields",
    });
    await dblclick(".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']");
    await animationFrame();
    expect(
        ".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids'] .o_add_field"
    ).toHaveClass("o_inactive", {
        message: "field has been added by double clicking on it and cannot be added anymore",
    });
    await contains(firstField + ".o_add_field").click();
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual([
        "Foo",
        "Company",
        "Activities",
    ]);
    await dblclick(".o_export_tree_item[data-field_id='activity_ids']");
    await animationFrame();
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual(
        ["Foo", "Company", "Activities"],
        {
            message: "double clicking on an expandable field does not add the field",
        }
    );
    await contains(".o_export_field:first-child").dragAndDrop(
        queryFirst(".o_export_field:nth-child(2)")
    );
    await contains(".o_export_field:nth-child(3)").dragAndDrop(
        queryFirst(".o_export_field:first-child")
    );
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual([
        "Activities",
        "Company",
        "Foo",
    ]);
    await contains(".modal .o_export_field:nth-child(2) .o_remove_field").click();
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual(["Activities", "Foo"]);
    await contains(
        firstField +
            ".o_export_tree_item[data-field_id='activity_ids/partner_ids/name'] .o_add_field"
    ).click();
    expect(queryAllTexts(".o_right_field_panel .o_export_field")).toEqual([
        "Activities",
        "Foo",
        "Partner name",
    ]);
});

test("Export dialog: compatible and export type options", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            expect(JSON.parse(options.data.data)["import_compat"]).toBe(true);
        },
    });
    onRpc("/web/export/formats", () => {
        return [
            { tag: "csv", label: "CSV" },
            { tag: "xls", label: "Excel" },
            { tag: "wow", label: "WOW" },
        ];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();
    expect("input[name='o_export_format_name']").toHaveCount(3);
    expect("[name=o_export_format_name][value=csv]").toBeChecked();
    expect(".o_export_format div:nth-of-type(3)").toHaveText("WOW");
    await check(".o_export_format div:nth-of-type(3) input");
    await animationFrame();
    await contains(".o_import_compat input").click();
    await contains(".o_select_button").click();
    // download file has been called with the correct url
    expect.verifySteps(["/web/export/wow"]);
});

test("toggling import compatibility after adding an expanded field", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            expect(JSON.parse(options.data.data)["import_compat"]).toBe(true);
        },
    });
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    await contains("[data-field_id='activity_ids']").click();
    await contains("[data-field_id='activity_ids/partner_ids'] .o_add_field").click();
    await contains(".o_import_compat input").click();
    await contains("[data-field_id='activity_ids']").click();
    await contains(".o_select_button").click();
    // download file has been called with the correct url
    expect.verifySteps(["/web/export/csv"]);
});

test("Export dialog: many2many fields are extendable", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    await contains("[data-field_id='activity_ids']").click();
    expect(queryFirst("[data-field_id='activity_ids/mail_template_ids'] span")).toHaveClass(
        "o_expand_parent",
        {
            message: "many2many element is expandable",
        }
    );
});

test("Export dialog: export list with 'exportable: false'", async () => {
    Partner._fields.not_exportable = fields.Char({ string: "Not exportable", exportable: false });
    Partner._fields.exportable = fields.Char();
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return [
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
            ];
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1">
            <field name="foo"/>
            <field name="not_exportable"/>
            <field name="exportable"/>
        </list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    expect(".o_export_field").toHaveCount(2);
    expect(".o_fields_list").toHaveText("Foo\nExportable");
});

test.tags("desktop");
test("Export dialog: sortable on desktop", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    await contains(".modal .o_export_tree_item .o_add_field").click();
    expect(".o_export_field_sortable").toHaveCount(2, {
        message: "exported fields can be sorted by drag and drop",
    });
});

test.tags("mobile");
test("Export dialog: non-sortable on mobile", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();

    await contains(".modal .o_export_tree_item .o_add_field").click();
    expect(".o_export_field_sortable").toHaveCount(0, {
        message: "exported fields can't be sorted by drag and drop",
    });
});

test.tags("desktop");
test("ExportDialog: export all records of the domain", async () => {
    let isDomainSelected = false;
    patchWithCleanup(download, {
        _download: (options) => {
            if (isDomainSelected) {
                expect(JSON.parse(options.data.data).ids).toBe(false);
                expect.step("download called with correct params when all records are selected");
            } else {
                expect(JSON.parse(options.data.data).ids).toEqual([1]);
                expect.step("download called with correct params when only one record is selected");
            }
        },
    });
    onRpc("/web/export/formats", () => {
        return [{ tag: "xls", label: "Excel" }];
    });
    onRpc("/web/export/get_fields", async (request) =>  {
        const { params } = await request.json();
        if (isDomainSelected) {
            const expectedDomain = params.parent_field ? [] : [["bar", "!=", "glou"]];
            expect(params.domain).toEqual(expectedDomain, {message: "Domain is only applied on the root model"});
            expect.step("get export fields route called with correct domain");
        }
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list export_xlsx="1" limit="1">
            <field name="foo"/>
            <field name="bar"/>
        </list>`,
        loadActionMenus: true,
        domain: [["bar", "!=", "glou"]],
    });

    await openExportDialog();

    await contains(".o_select_button").click();
    await contains(".o_form_button_cancel").click();

    isDomainSelected = true;
    await contains(".o_list_select_domain").click();
    await contains(".o_control_panel .o_cp_action_menus .dropdown-toggle").click();
    await contains(".dropdown-menu span:contains(Export)").click();
    await contains(".o_select_button").click();

    const firstField = ".o_left_field_panel .o_export_tree_item:first-child ";
    await contains(firstField).click();

    expect.verifySteps([
        "download called with correct params when only one record is selected",
        "get export fields route called with correct domain",
        "download called with correct params when all records are selected",
        "get export fields route called with correct domain",
    ]);
});

test("Direct export list", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect(options.url).toBe("/web/export/xlsx");
            expect(JSON.parse(options.data.data)).toEqual({
                context: { allowed_company_ids: [1], lang: "en", uid: 7, tz: "taht" },
                model: "partner",
                domain: [["bar", "!=", "glou"]],
                groupby: [],
                ids: false,
                import_compat: false,
                fields: [
                    {
                        name: "foo",
                        label: "Foo",
                        store: true,
                        type: "char",
                    },
                    {
                        name: "bar",
                        label: "Bar",
                        store: true,
                        type: "boolean",
                    },
                ],
            });
        },
    });
    onRpc("/web/export/formats", () => {
        return [{ tag: "xls", label: "Excel" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list export_xlsx="1">
            <field name="foo"/>
            <field name="bar"/>
        </list>`,
        loadActionMenus: true,
        domain: [["bar", "!=", "glou"]],
    });

    await exportAllAction();
});

test("Direct export grouped list", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect(JSON.parse(options.data.data).groupby).toEqual(["foo", "bar"]);
        },
    });
    onRpc("/web/export/formats", () => {
        return [{ tag: "xls", label: "Excel" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list export_xlsx="1">
            <field name="foo"/>
            <field name="bar"/>
        </list>`,
        loadActionMenus: true,
        groupBy: ["foo", "bar"],
        domain: [["bar", "!=", "glou"]],
    });

    await exportAllAction();
});

test.tags("desktop");
test("Direct export list take optional fields into account on desktop", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect(JSON.parse(options.data.data).fields).toEqual([
                { label: "Bar", name: "bar", store: true, type: "boolean" },
            ]);
        },
    });
    onRpc("/web/export/formats", () => {
        return [{ tag: "xls", label: "Excel" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list>
            <field name="foo" optional="show"/>
            <field name="bar" optional="show"/>
        </list>`,
        loadActionMenus: true,
    });

    await contains("table .o_optional_columns_dropdown .dropdown-toggle").click();
    await contains("span.dropdown-item:first-child").click();
    expect("th").toHaveCount(3, {
        message: "should have 3 th, 1 for selector, 1 for columns, 1 for optional columns",
    });
    await exportAllAction();
});

test.tags("mobile");
test("Direct export list take optional fields into account on mobile", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect(JSON.parse(options.data.data).fields).toEqual([
                { label: "Bar", name: "bar", store: true, type: "boolean" },
            ]);
        },
    });
    onRpc("/web/export/formats", () => {
        return [{ tag: "xls", label: "Excel" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list>
            <field name="foo" optional="show"/>
            <field name="bar" optional="show"/>
        </list>`,
        loadActionMenus: true,
    });

    await contains("table .o_optional_columns_dropdown .dropdown-toggle").click();
    await contains("span.dropdown-item:first-child").click();
    expect("th").toHaveCount(2, {
        message: "should have 2 th, 1 for columns, 1 for optional columns",
    });
    await exportAllAction();
});

test.tags("desktop");
test("Export dialog with duplicated fields on desktop", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list>
            <field name="foo" string="Foo"/>
            <field name="foo" string="duplicate of Foo"/>
        </list>`,
        loadActionMenus: true,
    });

    expect(".o_list_table th:nth-child(2)").toHaveText("Foo");
    expect(".o_list_table th:nth-child(3)").toHaveText("duplicate of Foo");
    await openExportDialog();
    expect(".modal .o_export_field").toHaveCount(1);
    expect(".modal .o_export_field").toHaveText("Foo", {
        message: "the only field to export corresponds to the field displayed in the list view",
    });
});

test.tags("mobile");
test("Export dialog with duplicated fields on mobile", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list>
            <field name="foo" string="Foo"/>
            <field name="foo" string="duplicate of Foo"/>
        </list>`,
        loadActionMenus: true,
    });

    expect(".o_list_table th:nth-child(1)").toHaveText("Foo");
    expect(".o_list_table th:nth-child(2)").toHaveText("duplicate of Foo");
    await openExportDialog();
    expect(".modal .o_export_field").toHaveCount(1);
    expect(".modal .o_export_field").toHaveText("Foo", {
        message: "the only field to export corresponds to the field displayed in the list view",
    });
});

test("Export dialog: export list contains field with 'default_export: true'", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return [
                ...fetchedFields.root,
                {
                    id: "default_exportable",
                    string: "Default exportable",
                    type: "char",
                    default_export: true,
                },
            ];
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
        <list>
            <field name="foo" string="Foo"/>
            <field name="foo" string="duplicate of Foo"/>
        </list>`,
        loadActionMenus: true,
    });

    await openExportDialog();
    expect(".modal .o_export_field").toHaveCount(2);
    expect(".o_fields_list").toHaveText("Foo\nDefault exportable");
});

test("Export dialog: search subfields", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();
    const firstField = ".o_left_field_panel .o_export_tree_item:first-child ";
    await contains(firstField).click();
    // show then hide content for the 'partner_ids' field.
    // this will load subfields and make them available to search
    await contains(firstField + ".o_export_tree_item").click();
    await contains(firstField + ".o_export_tree_item").click();
    await contains(".o_export_search_input").edit("company");
    expect(".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']").toHaveCount(
        1,
        {
            message: "subfield that was known has been found and is displayed",
        }
    );
});

test("Export dialog: expand subfields after search", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();
    const firstField = ".o_left_field_panel .o_export_tree_item:first-child ";
    await contains(firstField).click();
    // show then hide content for the 'partner_ids' field.
    // this will load subfields and make them available to search
    await contains(firstField).click();
    await contains(firstField).click();
    await contains(".o_export_search_input").edit("Attendants");
    expect(".o_export_tree_item[data-field_id='activity_ids/partner_ids']").toHaveCount(1, {
        message: "subfield that was known has been found and is displayed",
    });
    await contains(".o_export_tree_item[data-field_id='activity_ids/partner_ids']").click();
    // 'Company' should be shown even if the company_ids string doesn't match the search string
    // since the toggle was done by the user to show subfields
    expect(".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']").toHaveCount(
        1,
        {
            message: "subfield has been loaded and is displayed",
        }
    );
});

test("Export dialog: search in debug", async () => {
    serverState.debug = true;

    onRpc("/web/export/formats", () => {
        return [{ tag: "csv", label: "CSV" }];
    });
    onRpc("/web/export/get_fields", async (request) => {
        const { params } = await request.json();
        if (!params.parent_field) {
            return fetchedFields.root;
        }
        return fetchedFields[params.prefix];
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();
    await contains(".o_left_field_panel .o_export_tree_item:first-child").click();
    await contains(".o_export_tree_item:first-child .o_export_tree_item").click();
    await contains(".o_export_search_input").edit("company_ids");
    expect(".o_export_tree_item[data-field_id='activity_ids/partner_ids/company_ids']").toHaveCount(
        1,
        {
            message: "subfield has been found with its technical name and is displayed",
        }
    );
});

test("Export dialog: disable button during export", async () => {
    let def;
    patchWithCleanup(download, {
        _download: () => (def = new Deferred()),
    });
    onRpc("/web/export/formats", () => {
        return [{ tag: "xls", label: "Excel" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list export_xlsx="1"><field name="foo"/></list>`,
        loadActionMenus: true,
    });

    await openExportDialog();
    expect(".o_select_button").toBeEnabled();
    await contains(".o_select_button").click();
    expect(".o_select_button").not.toBeEnabled();
    def.resolve();
    await animationFrame();
    expect(".o_select_button").toBeEnabled();
});

test("Export dialog: no column_invisible fields in default export list", async () => {
    onRpc("/web/export/formats", () => {
        return [{ tag: "xls", label: "Excel" }];
    });
    onRpc("/web/export/get_fields", () => {
        return fetchedFields.root;
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list>
                <field name="foo"/>
                <field name="bar" column_invisible="1"/>
            </list>`,
        actionMenus: {},
    });

    await openExportDialog();
    expect(".modal .o_export_field").toHaveCount(1);
    expect(".modal .o_export_field").toHaveText("Foo");
});
