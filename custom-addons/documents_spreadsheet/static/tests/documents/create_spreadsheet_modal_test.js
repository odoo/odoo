/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { documentService } from "@documents/core/document_service";
import { getEnrichedSearchArch } from "@documents/../tests/documents_test_utils";

import { start } from "@mail/../tests/helpers/test_utils";

import {
    editInput,
    triggerEvent,
    getFixture,
    click,
    patchWithCleanup,
    nextTick,
} from "@web/../tests/helpers/utils";
import { getBasicData } from "@spreadsheet/../tests/utils/data";

import { mockActionService } from "@documents_spreadsheet/../tests/spreadsheet_test_utils";
import { companyService } from "@web/webclient/company_service";
import { session } from "@web/session";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { makeFakeSpreadsheetService } from "@spreadsheet_edition/../tests/utils/collaborative_helpers";

const serviceRegistry = registry.category("services");

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

async function getDocumentBasicData(views = {}) {
    const pyEnv = await startServer();
    const documentsFolderId1 = pyEnv["documents.folder"].create({
        name: "Workspace1",
        description: "Workspace",
        has_write_access: true,
    });
    const mailAliasId1 = pyEnv["mail.alias"].create({ alias_name: "hazard@rmcf.es" });
    pyEnv["documents.share"].create({
        name: "Share1",
        folder_id: documentsFolderId1,
        alias_id: mailAliasId1,
    });
    pyEnv["spreadsheet.template"].create([
        { name: "Template 1", spreadsheet_data: "{}" },
        { name: "Template 2", spreadsheet_data: "{}" },
    ]);
    return {
        models: {
            ...getBasicData(),
            ...pyEnv.getData(),
        },
        views,
    };
}

/**
 * @typedef InitArgs
 * @property {Object} serverData
 * @property {Array} additionalTemplates
 * @property {Function} mockRPC
 */

/**
 *  @param {InitArgs} args
 */
async function initTestEnvWithKanban(args = {}) {
    const data =
        args.serverData ||
        (await getDocumentBasicData({
            "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
        }));
    data.models["spreadsheet.template"].records = data.models[
        "spreadsheet.template"
    ].records.concat(args.additionalTemplates || []);
    Object.assign(data.views, {
        "documents.document,false,kanban": `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div><field name="name"/></div>
            </t></templates></kanban>
        `,
        "documents.document,false,search": getEnrichedSearchArch(),
    });
    const res = await start({
        mockRPC: args.mockRPC || (() => {}),
        serverData: data,
    });
    const { openView } = res;
    await openView({
        res_model: "documents.document",
        views: [[false, "kanban"]],
    });
    return res;
}

/**
 *  @param {InitArgs} args
 */
async function initTestEnvWithBlankSpreadsheet(params = {}) {
    const pyEnv = await startServer();
    const documentsFolderId1 = pyEnv["documents.folder"].create({ has_write_access: true });
    pyEnv["documents.document"].create({
        name: "My spreadsheet",
        spreadsheet_data: "{}",
        is_favorited: false,
        folder_id: documentsFolderId1,
        handler: "spreadsheet",
    });
    const serverData = {
        models: pyEnv.getData(),
        views: {
            "spreadsheet.template,false,search": `<search><field name="name"/></search>`,
        },
    };
    return await initTestEnvWithKanban({ serverData, ...params });
}

let target;

QUnit.module(
    "documents_spreadsheet > create spreadsheet from template modal",
    {
        beforeEach() {
            setupViewRegistries();
            target = getFixture();
            serviceRegistry.add("document.document", documentService);
            serviceRegistry.add("file_upload", fileUploadService);
            serviceRegistry.add("documents_pdf_thumbnail", {
                start() {
                    return {
                        enqueueRecords: () => {},
                    };
                },
            });

            patchWithCleanup(session.user_companies.allowed_companies[1], {
                documents_spreadsheet_folder_id: 1,
            });

            serviceRegistry.add("company", companyService, { force: true });
        },
    },
    () => {
        QUnit.test("Create spreadsheet from kanban view opens a modal", async function (assert) {
            await initTestEnvWithKanban();
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            assert.containsOnce(
                target,
                ".o-spreadsheet-templates-dialog",
                "should have opened the template modal"
            );
            assert.containsOnce(
                target,
                ".o-spreadsheet-templates-dialog .modal-body .o_searchview",
                "The Modal should have a search view"
            );
        });

        QUnit.test("Create spreadsheet from list view opens a modal", async function (assert) {
            const serverData = await getDocumentBasicData({
                "documents.document,false,list": `<tree js_class="documents_list"></tree>`,
                "documents.document,false,search": getEnrichedSearchArch(),
            });
            const { openView } = await start({ serverData });
            await openView({
                res_model: "documents.document",
                views: [[false, "list"]],
            });
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            assert.containsOnce(
                target,
                ".o-spreadsheet-templates-dialog",
                "should have opened the template modal"
            );
            assert.containsOnce(
                target,
                ".o-spreadsheet-templates-dialog .modal-body .o_searchview",
                "The Modal should have a search view"
            );
        });

        QUnit.test("Can search template in modal with searchbar", async function (assert) {
            await initTestEnvWithKanban();
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            const dialog = target.querySelector(".o-spreadsheet-templates-dialog");
            assert.equal(
                dialog.querySelectorAll(".o-template:not(.o-template-ghost-item)").length,
                3
            );
            assert.equal(dialog.querySelector(".o-template").textContent, "Blank spreadsheet");

            const searchInput = dialog.querySelector(".o_searchview_input");
            await editInput(searchInput, null, "Template 1");
            await triggerEvent(searchInput, null, "keydown", { key: "Enter" });
            assert.equal(
                dialog.querySelectorAll(".o-template:not(.o-template-ghost-item)").length,
                2
            );
            assert.equal(dialog.querySelector(".o-template").textContent, "Blank spreadsheet");
        });

        QUnit.test("Can fetch next templates", async function (assert) {
            let fetch = 0;
            const mockRPC = async function (route, args) {
                if (args.method === "web_search_read" && args.model === "spreadsheet.template") {
                    fetch++;
                    assert.equal(args.kwargs.limit, 9);
                    assert.step("fetch_templates");
                    if (fetch === 1) {
                        assert.equal(args.kwargs.offset, 0);
                    } else if (fetch === 2) {
                        assert.equal(args.kwargs.offset, 9);
                    }
                }
                if (args.method === "search_read" && args.model === "ir.model") {
                    return [{ name: "partner" }];
                }
            };
            await initTestEnvWithKanban({ additionalTemplates: TEST_TEMPLATES, mockRPC });

            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");

            assert.equal(
                dialog.querySelectorAll(".o-template:not(.o-template-ghost-item)").length,
                10
            );
            await click(dialog.querySelector(".o_pager_next"));
            assert.verifySteps(["fetch_templates", "fetch_templates"]);
        });

        QUnit.test("Disable create button if no template is selected", async function (assert) {
            assert.expect(2);
            await initTestEnvWithKanban({ additionalTemplates: TEST_TEMPLATES });
            // open template dialog
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");

            // select template
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[1], null, "focus");

            // change page; no template should be selected
            await click(dialog.querySelector(".o_pager_next"));
            assert.containsNone(dialog, ".o-template-selected");
            const createButton = dialog.querySelector(".o-spreadsheet-create");
            assert.ok(createButton.attributes.disabled);
        });

        QUnit.test("Can create a blank spreadsheet from template dialog", async function (assert) {
            const mockDoAction = (action) => {
                assert.step("redirect");
                assert.equal(action.tag, "action_open_spreadsheet");
            };
            const { env } = await initTestEnvWithBlankSpreadsheet({
                mockRPC: async function (route, args) {
                    if (
                        args.model === "documents.document" &&
                        args.method === "action_open_new_spreadsheet"
                    ) {
                        assert.strictEqual(args.args[0].folder_id, 1);
                        assert.step("action_open_new_spreadsheet");
                    }
                },
            });
            mockActionService(env, mockDoAction);

            // ### With confirm button
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            let dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            // select blank spreadsheet
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[0], null, "focus");
            await click(dialog.querySelector(".o-spreadsheet-create"));
            assert.verifySteps(["action_open_new_spreadsheet", "redirect"]);

            // ### With double click on image
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[0], null, "focus");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[0], null, "dblclick");
            assert.verifySteps(["action_open_new_spreadsheet", "redirect"]);

            // ### With enter key
            await click(menu, ".o_documents_kanban_spreadsheet");
            dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[0], null, "focus");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[0], null, "keydown", {
                key: "Enter",
            });
            assert.verifySteps(["action_open_new_spreadsheet", "redirect"]);
        });
        QUnit.test("Context is transmitted when creating spreadsheet", async function (assert) {
            const serverData = await getDocumentBasicData({
                "documents.document,false,kanban": `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div><field name="name"/></div>
                </t></templates></kanban>
                `,
                "documents.document,false,search": getEnrichedSearchArch(),
            });
            serviceRegistry.add("spreadsheet_collaborative", makeFakeSpreadsheetService());
            const { openView } = await start({
                mockRPC: async function (route, args) {
                    if (args.method === "action_open_new_spreadsheet") {
                        assert.step("action_open_new_spreadsheet");
                        assert.strictEqual(args.kwargs.context.default_res_id, 42);
                        assert.strictEqual(args.kwargs.context.default_res_model, "test.model");
                    }
                },
                serverData,
            });
            await openView({
                context: {
                    default_res_model: "test.model",
                    default_res_id: 42,
                },
                res_model: "documents.document",
                views: [[false, "kanban"]],
            });

            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            const dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            // select blank spreadsheet
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[0], null, "focus");
            await click(dialog, ".o-spreadsheet-create");
            assert.verifySteps(["action_open_new_spreadsheet"]);
        });

        QUnit.test("Can create a spreadsheet from a template", async function (assert) {
            const mockDoAction = (action) => {
                assert.step("redirect");
                assert.equal(action.tag, "an_action");
            };
            const { env } = await initTestEnvWithKanban({
                additionalTemplates: TEST_TEMPLATES,
                mockRPC: async function (route, args) {
                    if (
                        args.model === "spreadsheet.template" &&
                        args.method === "action_create_spreadsheet"
                    ) {
                        assert.step("action_create_spreadsheet");
                        assert.strictEqual(args.args[1].folder_id, 1);
                        const action = {
                            type: "ir.actions.client",
                            tag: "an_action",
                        };
                        return action;
                    }
                },
            });
            mockActionService(env, mockDoAction);

            // ### With confirm button
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            let dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            // select blank spreadsheet
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[1], null, "focus");
            await click(dialog.querySelector(".o-spreadsheet-create"));
            assert.verifySteps(["action_create_spreadsheet", "redirect"]);

            // ### With double click on image
            await click(menu, ".dropdown-toggle");
            await click(menu, ".o_documents_kanban_spreadsheet");
            dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[1], null, "focus");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[1], null, "dblclick");
            assert.verifySteps(["action_create_spreadsheet", "redirect"]);

            // ### With enter key
            await click(menu, ".o_documents_kanban_spreadsheet");
            dialog = document.querySelector(".o-spreadsheet-templates-dialog");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[1], null, "focus");
            await triggerEvent(dialog.querySelectorAll(".o-template-image")[1], null, "keydown", {
                key: "Enter",
            });
            assert.verifySteps(["action_create_spreadsheet", "redirect"]);
        });

        QUnit.test(
            "The workspace selection should not display Trash workspace",
            async function (assert) {
                await initTestEnvWithKanban();
                const menu = target.querySelector(
                    ".o_control_panel .btn-group:not(.o_control_panel_collapsed_create .btn-group)"
                );
                await click(target, ".o_search_panel_category_value:nth-of-type(1) header");
                await click(menu, ".dropdown-toggle");
                await click(menu, ".o_documents_kanban_spreadsheet");
                const selection = target.querySelector(".o-spreadsheet-templates-dialog select");
                assert.notOk(
                    [...selection.options].find((option) => option.value === "TRASH"),
                    "Trash workspace should not be present in the selection"
                );
            }
        );

        QUnit.test(
            "Offset reset to zero after searching for template in template dialog",
            async function (assert) {
                const mockRPC = async function (route, args) {
                    if (
                        args.method === "web_search_read" &&
                        args.model === "spreadsheet.template"
                    ) {
                        assert.step(
                            JSON.stringify({
                                offset: args.kwargs.offset,
                                limit: args.kwargs.limit,
                            })
                        );
                    }
                };

                await initTestEnvWithKanban({ additionalTemplates: TEST_TEMPLATES, mockRPC });

                const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
                await click(menu, ".dropdown-toggle");
                await click(menu, ".o_documents_kanban_spreadsheet");
                const dialog = document.querySelector(".o-spreadsheet-templates-dialog");

                assert.equal(
                    dialog.querySelectorAll(".o-template:not(.o-template-ghost-item)").length,
                    10
                );
                await click(dialog.querySelector(".o_pager_next"));
                assert.verifySteps([
                    JSON.stringify({ offset: 0, limit: 9 }),
                    JSON.stringify({ offset: 9, limit: 9 }),
                ]);

                const searchInput = dialog.querySelector(".o_searchview_input");
                await editInput(searchInput, null, "Template 1");
                await triggerEvent(searchInput, null, "keydown", { key: "Enter" });
                await nextTick();

                assert.equal(
                    dialog.querySelectorAll(".o-template:not(.o-template-ghost-item)").length,
                    5
                ); // Blank template, Template 1, Template 10, Template 11, Template 12
                assert.verifySteps([JSON.stringify({ offset: 0, limit: 9 })]);
                assert.strictEqual(
                    target.querySelector(".o_pager_value").textContent,
                    "1-4",
                    "Pager should be reset to 1-4 after searching for a template"
                );
            }
        );
    }
);
