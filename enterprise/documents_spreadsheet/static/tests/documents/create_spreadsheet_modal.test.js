import {
    defineDocumentSpreadsheetModels,
    getDocumentBasicData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { getEnrichedSearchArch } from "@documents/../tests/helpers/views/search";
import { mockActionService } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { describe, expect, test } from "@odoo/hoot";
import { click, dblclick, queryFirst, select } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { makeDocumentsSpreadsheetMockEnv } from "@documents_spreadsheet/../tests/helpers/model";
import { contains, mountView } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineDocumentSpreadsheetModels();

const kanbanArch = /* xml */ `
    <kanban js_class="documents_kanban">
        <templates>
            <field name="id"/>
            <field name="available_embedded_actions_ids"/>
            <field name="access_token"/>
            <field name="mimetype"/>
            <field name="folder_id"/>
            <field name="owner_id"/>
            <field name="active"/>
            <field name="type"/>
            <field name="attachment_id"/>
            <t t-name="card">
                <div><field name="name"/></div>
            </t>
        </templates>
    </kanban>`;

const TEST_TEMPLATES = [
    { id: 3, name: "Template 3", spreadsheet_data: "{}" },
    { id: 4, name: "Template 4", spreadsheet_data: "{}" },
    { id: 5, name: "Template 5", spreadsheet_data: "{}" },
    { id: 6, name: "Template 6", spreadsheet_data: "{}" },
    { id: 7, name: "Template 7", spreadsheet_data: "{}" },
    { id: 8, name: "Template 8", spreadsheet_data: "{}" },
    { id: 9, name: "Template 9", spreadsheet_data: "{}" },
    { id: 10, name: "Template 10", spreadsheet_data: "{}" },
    { id: 11, name: "Template 11", spreadsheet_data: "{}" },
    { id: 12, name: "Template 12", spreadsheet_data: "{}" },
];

/**
 * @typedef InitArgs
 * @property {Object} [serverData]
 * @property {Array} [additionalTemplates]
 * @property {Function} [mockRPC]
 */

/**
 *  @param {InitArgs} args
 */
async function initTestEnvWithKanban(args = {}) {
    const data = args.serverData || getDocumentBasicData({});
    data.models["spreadsheet.template"].records = data.models[
        "spreadsheet.template"
    ].records.concat(args.additionalTemplates || []);
    await makeDocumentsSpreadsheetMockEnv({ ...args, serverData: data });
    return mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: kanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
}

/**
 *  @param {InitArgs} params
 */
async function initTestEnvWithBlankSpreadsheet(params = {}) {
    const serverData = getDocumentBasicData();
    serverData.models["documents.document"] = {
        records: [
            {
                name: "Folder 1",
                description: "Folder",
                type: "folder",
                id: 1,
                available_embedded_actions_ids: [],
            },
        ],
    };
    serverData.models["documents.document"] = {
        record: [
            {
                name: "My spreadsheet",
                spreadsheet_data: "{}",
                is_favorited: false,
                folder_id: 1,
                handler: "spreadsheet",
            },
        ],
    };
    return initTestEnvWithKanban({ serverData, ...params });
}

async function openTemplateDialog() {
    await contains(`.o_control_panel .btn-group .dropdown-toggle`).click();
    await contains(`.o_control_panel .btn-group .o_documents_kanban_spreadsheet`).click();
}

const dialogSelector = ".o-spreadsheet-templates-dialog";

test("Create spreadsheet from kanban view opens a modal", async function () {
    await initTestEnvWithKanban();
    await openTemplateDialog();

    expect(".o-spreadsheet-templates-dialog").toHaveCount(1, {
        message: "should have opened the template modal",
    });
    expect(".o-spreadsheet-templates-dialog .modal-body .o_searchview").toHaveCount(1, {
        message: "The Modal should have a search view",
    });
});

test("Create spreadsheet from list view opens a modal", async function () {
    const serverData = getDocumentBasicData();
    await makeDocumentsSpreadsheetMockEnv({ serverData });
    await mountView({
        resModel: "documents.document",
        type: "list",
        arch: `<list js_class="documents_list"></list>`,
        searchViewArch: getEnrichedSearchArch(),
    });
    await openTemplateDialog();

    expect(".o-spreadsheet-templates-dialog").toHaveCount(1, {
        message: "should have opened the template modal",
    });
    expect(".o-spreadsheet-templates-dialog .modal-body .o_searchview").toHaveCount(1, {
        message: "The Modal should have a search view",
    });
});

test("Can search template in modal with searchbar", async function () {
    await initTestEnvWithKanban();
    await openTemplateDialog();

    expect(`${dialogSelector} .o-spreadsheet-grid:not(.o-spreadsheet-grid-ghost-item)`).toHaveCount(
        3
    );
    expect(`${dialogSelector} .o-spreadsheet-grid:first`).toHaveText("Blank spreadsheet");

    await contains(`${dialogSelector} .o_searchview_input`).edit("Template 1");
    expect(`${dialogSelector} .o-spreadsheet-grid:not(.o-spreadsheet-grid-ghost-item)`).toHaveCount(
        2
    );
    expect(`${dialogSelector} .o-spreadsheet-grid:first`).toHaveText("Blank spreadsheet");
});

test("Can fetch next templates", async function () {
    let fetch = 0;
    const mockRPC = async function (route, args) {
        if (args.method === "web_search_read" && args.model === "spreadsheet.template") {
            fetch++;
            expect(args.kwargs.limit).toBe(9);
            expect.step("fetch_templates");
            if (fetch === 1) {
                expect(args.kwargs.offset).toBe(0);
            } else if (fetch === 2) {
                expect(args.kwargs.offset).toBe(9);
            }
        }
        if (args.method === "search_read" && args.model === "ir.model") {
            return [{ name: "partner" }];
        }
    };
    await initTestEnvWithKanban({ additionalTemplates: TEST_TEMPLATES, mockRPC });
    await openTemplateDialog();

    expect(`${dialogSelector} .o-spreadsheet-grid:not(.o-spreadsheet-grid-ghost-item)`).toHaveCount(
        10
    );
    await contains(`${dialogSelector} .o_pager_next`).click();
    expect.verifySteps(["fetch_templates", "fetch_templates"]);
});

test("Disable create button if no template is selected", async function () {
    await initTestEnvWithKanban({ additionalTemplates: TEST_TEMPLATES });
    await openTemplateDialog();

    // select template
    await click(`${dialogSelector} .o-spreadsheet-grid-image:eq(1)`);

    // change page; no template should be selected
    await contains(`${dialogSelector} .o_pager_next`).click();
    expect(".o-spreadsheet-grid-selected").toHaveCount(0);
    expect(`${dialogSelector} .o-spreadsheet-create`).toHaveAttribute("disabled");
});

test("Can create a blank spreadsheet from template dialog", async function () {
    const mockDoAction = (action) => {
        expect.step("redirect");
        expect(action.tag).toBe("action_open_spreadsheet");
    };
    await initTestEnvWithBlankSpreadsheet({
        mockRPC: async function (route, args) {
            if (
                args.model === "documents.document" &&
                args.method === "action_open_new_spreadsheet"
            ) {
                expect(args.args[0].folder_id).toBe(1);
                expect.step("action_open_new_spreadsheet");
            }
        },
    });
    mockActionService(mockDoAction);

    // ### With confirm button
    await openTemplateDialog();

    // select blank spreadsheet
    await click(`${dialogSelector} .o-spreadsheet-grid-image`);
    await contains(`${dialogSelector} .o-spreadsheet-create`).click();
    expect.verifySteps(["action_open_new_spreadsheet", "redirect"]);

    // ### With double click on image
    await openTemplateDialog();

    await click(`${dialogSelector} .o-spreadsheet-grid-image`);
    await dblclick(`${dialogSelector} .o-spreadsheet-grid-image`);
    await animationFrame();
    expect.verifySteps(["action_open_new_spreadsheet", "redirect"]);
});

test("Context is transmitted when creating spreadsheet", async function () {
    const serverData = await getDocumentBasicData({
        "documents.document,false,kanban": `
                <kanban js_class="documents_kanban">
                    <field name="available_embedded_actions_ids"/>
                    <field name="access_token"/>
                    <field name="id"/>
                    <field name="mimetype"/>
                    <field name="folder_id"/>
                    <field name="active"/>
                    <field name="type"/>
                    <field name="attachment_id"/>
                    <templates>
                        <t t-name="card">
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>
                `,
        "documents.document,false,search": getEnrichedSearchArch(),
    });
    await makeDocumentsSpreadsheetMockEnv({
        mockRPC: async function (route, args) {
            if (args.method === "action_open_new_spreadsheet") {
                expect.step("action_open_new_spreadsheet");
                expect(args.kwargs.context.default_res_id).toBe(42);
                expect(args.kwargs.context.default_res_model).toBe("test.model");
            }
        },
        serverData,
    });
    await mountView({
        context: {
            default_res_model: "test.model",
            default_res_id: 42,
        },
        resModel: "documents.document",
        type: "kanban",
        searchViewArch: getEnrichedSearchArch(),
        arch: kanbanArch,
    });

    await openTemplateDialog();

    // select blank spreadsheet
    await click(`${dialogSelector} .o-spreadsheet-grid-image`);
    await contains(`${dialogSelector} .o-spreadsheet-create`).click();
    expect.verifySteps(["action_open_new_spreadsheet"]);
});

test("Can create a spreadsheet from a template", async function () {
    const mockDoAction = (action) => {
        expect.step("redirect");
        expect(action.tag).toBe("an_action");
    };
    await initTestEnvWithKanban({
        additionalTemplates: TEST_TEMPLATES,
        mockRPC: async function (route, args) {
            if (
                args.model === "spreadsheet.template" &&
                args.method === "action_create_spreadsheet"
            ) {
                expect.step("action_create_spreadsheet");
                expect(args.args[1].folder_id).toBe(1);
                const action = {
                    type: "ir.actions.client",
                    tag: "an_action",
                };
                return action;
            }
        },
    });
    mockActionService(mockDoAction);

    // ### With confirm button
    await openTemplateDialog();

    await click(`${dialogSelector} .o-spreadsheet-grid-image:eq(1)`);
    await contains(`${dialogSelector} .o-spreadsheet-create`).click();
    expect.verifySteps(["action_create_spreadsheet", "redirect"]);

    // ### With double click on image
    await openTemplateDialog();
    await click(`${dialogSelector} .o-spreadsheet-grid-image:eq(1)`);
    await dblclick(`${dialogSelector} .o-spreadsheet-grid-image:eq(1)`);
    await animationFrame();
    expect.verifySteps(["action_create_spreadsheet", "redirect"]);
});

test("The workspace selection should not display Trash workspace", async function () {
    await initTestEnvWithKanban();
    await openTemplateDialog();

    expect(
        ".o-spreadsheet-templates-dialog .o-spreadsheet-grid-item-name:contains(TRASH)"
    ).toHaveCount(0, {
        message: "Trash workspace should not be present in the selection",
    });
});

test("Offset reset to zero after searching for template in template dialog", async function () {
    const mockRPC = async function (route, args) {
        if (args.method === "web_search_read" && args.model === "spreadsheet.template") {
            expect.step(
                JSON.stringify({
                    offset: args.kwargs.offset,
                    limit: args.kwargs.limit,
                })
            );
        }
    };

    await initTestEnvWithKanban({ additionalTemplates: TEST_TEMPLATES, mockRPC });
    await openTemplateDialog();

    expect(`${dialogSelector} .o-spreadsheet-grid:not(.o-spreadsheet-grid-ghost-item)`).toHaveCount(
        10
    );
    await contains(`${dialogSelector} .o_pager_next`).click();
    expect.verifySteps([
        JSON.stringify({ offset: 0, limit: 9 }),
        JSON.stringify({ offset: 9, limit: 9 }),
    ]);

    await contains(`${dialogSelector} .o_searchview_input`).edit("Template 1");
    await animationFrame();
    await animationFrame();

    expect(`${dialogSelector} .o-spreadsheet-grid:not(.o-spreadsheet-grid-ghost-item)`).toHaveCount(
        5
    ); // Blank template, Template 1, Template 10, Template 11, Template 12
    expect.verifySteps([JSON.stringify({ offset: 0, limit: 9 })]);
    expect(`${dialogSelector} .o_pager_value `).toHaveText("1-4", {
        message: "Pager should be reset to 1-4 after searching for a template",
    });
});

test("Can navigate through templates with keyboard", async function () {
    await initTestEnvWithKanban({ additionalTemplates: TEST_TEMPLATES });
    await openTemplateDialog();

    const defaultTemplate = queryFirst(
        `${dialogSelector} .o-spreadsheet-grid.o-blank-spreadsheet-grid .o-spreadsheet-grid-image`
    );
    expect(defaultTemplate).toHaveClass("o-spreadsheet-grid-selected");

    // Navigate to the next template
    await contains(defaultTemplate).press("ArrowRight");
    expect(defaultTemplate).not.toHaveClass("o-spreadsheet-grid-selected");

    const firstTemplate = queryFirst(`${dialogSelector} .o-spreadsheet-grid-image[data-id='1']`);
    expect(firstTemplate).toHaveClass("o-spreadsheet-grid-selected");

    // Navigate back to the previous template
    await contains(defaultTemplate).press("ArrowLeft");
    expect(firstTemplate).not.toHaveClass("o-spreadsheet-grid-selected");
    expect(defaultTemplate).toHaveClass("o-spreadsheet-grid-selected");
});

test("Can create a blank spreadsheet from template dialog in a specific folder", async function () {
    const mockDoAction = (action) => {
        expect.step("redirect");
        expect(action.tag).toBe("action_open_spreadsheet");
    };
    await initTestEnvWithBlankSpreadsheet({
        mockRPC: async function (route, args) {
            if (
                args.model === "documents.document" &&
                args.method === "action_open_new_spreadsheet"
            ) {
                expect(args.args[0].folder_id).toBe(1);
                expect.step("action_open_new_spreadsheet");
            }
        },
    });
    mockActionService(mockDoAction);

    await contains(".o_search_panel_section").click();

    await openTemplateDialog();

    await select("2", { target: ".o-spreadsheet-templates-dialog select" });

    await contains(`${dialogSelector} .o-spreadsheet-grid-image`).click();
    await contains(`${dialogSelector} .o-spreadsheet-create`).click();

    expect.verifySteps(["action_open_new_spreadsheet", "redirect"]);
});
