/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { documentService } from "@documents/core/document_service";
import { DocumentsSearchPanel } from "@documents/views/search/documents_search_panel";
import {
    getEnrichedSearchArch,
    createDocumentsViewWithMessaging,
} from "@documents/../tests/documents_test_utils";

import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";
import { mockActionService } from "@documents_spreadsheet/../tests/spreadsheet_test_utils";

import { start } from "@mail/../tests/helpers/test_utils";

import { Model } from "@odoo/o-spreadsheet";

import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import {
    click,
    getFixture,
    mockDownload,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { contains } from "@web/../tests/utils";

const serviceRegistry = registry.category("services");

let target;

QUnit.module(
    "documents_spreadsheet kanban",
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
            // Due to the search panel allowing double clicking on elements, the base
            // methods have a debounce time in order to not do anything on dblclick.
            // This patch removes those features
            patchWithCleanup(DocumentsSearchPanel.prototype, {
                toggleCategory() {
                    return SearchPanel.prototype.toggleCategory.call(this, ...arguments);
                },
                toggleFilterGroup() {
                    return SearchPanel.prototype.toggleFilterGroup.call(this, ...arguments);
                },
                toggleFilterValue() {
                    return SearchPanel.prototype.toggleFilterValue.call(this, ...arguments);
                },
            });
        },
    },
    () => {
        QUnit.test("download spreadsheet from the document inspector", async function (assert) {
            assert.expect(4);
            patchWithCleanup(browser, { setInterval: (fn) => fn(), clearInterval: () => {} });
            const pyEnv = await startServer();
            const documentsFolderId1 = pyEnv["documents.folder"].create({
                display_name: "Workspace1",
                has_write_access: true,
            });
            pyEnv["documents.document"].create({
                name: "My spreadsheet",
                spreadsheet_data: "{}",
                is_favorited: false,
                folder_id: documentsFolderId1,
                handler: "spreadsheet",
            });
            mockDownload((options) => {
                assert.step(options.url);
                assert.ok(options.data.zip_name);
                assert.ok(options.data.files);
            });
            const serverData = {
                views: {
                    "documents.document,false,kanban": `
                        <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                                <field name="handler"/>
                            </div>
                        </t></templates></kanban>
                    `,
                    "documents.document,false,search": getEnrichedSearchArch(),
                },
            };
            const { openView } = await start({
                serverData,
            });
            await openView({
                res_model: "documents.document",
                views: [[false, "kanban"]],
            });

            await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
            await click(target, "button.o_inspector_download");
            await nextTick();
            assert.verifySteps(["/spreadsheet/xlsx"]);
        });
        QUnit.test("share spreadsheet from the document inspector", async function (assert) {
            const pyEnv = await startServer();
            const folderId = pyEnv["documents.folder"].create({
                display_name: "Workspace1",
                has_write_access: true,
            });
            await loadBundle("spreadsheet.o_spreadsheet");
            const model = new Model();
            const documentId = pyEnv["documents.document"].create({
                name: "My spreadsheet",
                spreadsheet_data: JSON.stringify(model.exportData()),
                folder_id: folderId,
                handler: "spreadsheet",
            });
            const serverData = {
                views: {
                    "documents.document,false,kanban": `
                        <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                                <field name="handler"/>
                            </div>
                        </t></templates></kanban>
                    `,
                    "documents.document,false,search": getEnrichedSearchArch(),
                },
            };
            patchWithCleanup(browser, {
                navigator: {
                    ...browser.navigator,
                    clipboard: {
                        writeText: (url) => {
                            assert.step("share url copied");
                            assert.strictEqual(url, "localhost:8069/share/url/132465");
                        },
                    },
                },
            });
            const { openView } = await start({
                mockRPC: async (route, args) => {
                    if (args.method === "action_get_share_url") {
                        assert.step("spreadsheet_shared");
                        const [shareVals] = args.args;
                        assert.strictEqual(args.model, "documents.share");
                        const excel = JSON.parse(JSON.stringify(model.exportXLSX().files));
                        assert.deepEqual(shareVals, {
                            document_ids: [x2ManyCommands.set([documentId])],
                            folder_id: folderId,
                            type: "ids",
                            spreadsheet_shares: [
                                {
                                    spreadsheet_data: JSON.stringify(model.exportData()),
                                    document_id: documentId,
                                    excel_files: excel,
                                },
                            ],
                        });
                        return "localhost:8069/share/url/132465";
                    }
                },
                serverData,
            });
            await openView({
                res_model: "documents.document",
                views: [[false, "kanban"]],
            });
            await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
            await click(target, "button.o_inspector_share");
            await contains(".o_notification.border-success", {
                text: "The share url has been copied to your clipboard.",
            });
            assert.verifySteps(["spreadsheet_shared", "share url copied"]);
        });

        QUnit.test("share a selected spreadsheet from the share button", async function (assert) {
            const pyEnv = await startServer();
            const folderId = pyEnv["documents.folder"].create({
                display_name: "Workspace1",
                has_write_access: true,
            });
            await loadBundle("spreadsheet.o_spreadsheet");
            const model = new Model();
            const documentId = pyEnv["documents.document"].create({
                name: "My spreadsheet",
                spreadsheet_data: JSON.stringify(model.exportData()),
                folder_id: folderId,
                handler: "spreadsheet",
            });
            const serverData = {
                views: {
                    "documents.document,false,kanban": `
                        <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                                <field name="handler"/>
                            </div>
                        </t></templates></kanban>
                    `,
                    "documents.document,false,search": getEnrichedSearchArch(),
                },
            };
            const { openView } = await start({
                mockRPC: async (route, args) => {
                    if (args.method === "open_share_popup") {
                        assert.step("spreadsheet_shared");
                        const [shareVals] = args.args;
                        assert.strictEqual(args.model, "documents.share");
                        assert.deepEqual(shareVals.document_ids, [
                            x2ManyCommands.set([documentId]),
                        ]);
                        assert.strictEqual(shareVals.folder_id, folderId);
                        assert.strictEqual(shareVals.type, "ids");
                        assert.deepEqual(shareVals.spreadsheet_shares, [
                            {
                                spreadsheet_data: JSON.stringify(model.exportData()),
                                document_id: documentId,
                                excel_files: JSON.parse(JSON.stringify(model.exportXLSX().files)),
                            },
                        ]);
                        return "localhost:8069/share/url/132465";
                    }
                },
                serverData,
            });
            await openView({
                res_model: "documents.document",
                views: [[false, "kanban"]],
            });
            await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, "button.dropdown-item.o_documents_kanban_share_domain");
            assert.verifySteps(["spreadsheet_shared"]);
        });

        QUnit.test("share the full workspace from the share button", async function (assert) {
            const pyEnv = await startServer();
            const folderId = pyEnv["documents.folder"].create({
                display_name: "Workspace1",
                has_write_access: true,
            });
            await loadBundle("spreadsheet.o_spreadsheet");
            const model = new Model();
            const documentId = pyEnv["documents.document"].create({
                name: "My spreadsheet",
                spreadsheet_data: JSON.stringify(model.exportData()),
                folder_id: folderId,
                handler: "spreadsheet",
            });
            const serverData = {
                views: {
                    "documents.document,false,kanban": `
                        <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                                <field name="handler"/>
                            </div>
                        </t></templates></kanban>
                    `,
                    "documents.document,false,search": getEnrichedSearchArch(),
                },
            };
            const { openView } = await start({
                mockRPC: async (route, args) => {
                    if (args.method === "open_share_popup") {
                        assert.step("spreadsheet_shared");
                        const [shareVals] = args.args;
                        assert.strictEqual(args.model, "documents.share");
                        assert.strictEqual(shareVals.folder_id, folderId);
                        assert.strictEqual(shareVals.type, "domain");
                        assert.deepEqual(shareVals.domain, [["folder_id", "child_of", folderId]]);
                        assert.deepEqual(shareVals.spreadsheet_shares, [
                            {
                                spreadsheet_data: JSON.stringify(model.exportData()),
                                document_id: documentId,
                                excel_files: JSON.parse(JSON.stringify(model.exportXLSX().files)),
                            },
                        ]);
                        return "localhost:8069/share/url/132465";
                    }
                },
                serverData,
            });
            await openView({
                res_model: "documents.document",
                views: [[false, "kanban"]],
            });
            const menu = target.querySelector(".o_control_panel .d-xl-inline-flex .btn-group");
            await click(menu, ".dropdown-toggle");
            await click(menu, "button.dropdown-item.o_documents_kanban_share_domain");
            assert.verifySteps(["spreadsheet_shared"]);
        });

        QUnit.test("thumbnail size in document side panel", async function (assert) {
            assert.expect(9);
            const pyEnv = await startServer();
            const documentsFolderId1 = pyEnv["documents.folder"].create({
                display_name: "Workspace1",
                has_write_access: true,
            });
            pyEnv["documents.document"].create([
                {
                    name: "My spreadsheet",
                    spreadsheet_data: "{}",
                    is_favorited: false,
                    folder_id: documentsFolderId1,
                    handler: "spreadsheet",
                },
                {
                    name: "",
                    spreadsheet_data: "{}",
                    is_favorited: true,
                    folder_id: documentsFolderId1,
                    handler: "spreadsheet",
                },
                {
                    name: "",
                    spreadsheet_data: "{}",
                    folder_id: documentsFolderId1,
                    handler: "spreadsheet",
                },
            ]);
            const serverData = {
                views: {
                    "documents.document,false,kanban": `
                        <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                                <field name="handler"/>
                            </div>
                        </t></templates></kanban>
                    `,
                    "documents.document,false,search": getEnrichedSearchArch(),
                },
            };
            const { openView } = await start({
                serverData,
            });
            await openView({
                res_model: "documents.document",
                views: [[false, "kanban"]],
            });
            await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
            assert.containsOnce(target, ".o_documents_inspector_preview .o_document_preview");
            assert.equal(
                target.querySelector(".o_documents_inspector_preview .o_document_preview img")
                    .dataset.src,
                "/documents/image/1/268x130?field=thumbnail&unique="
            );
            await click(target, ".o_kanban_record:nth-of-type(2) .o_record_selector");
            assert.containsN(target, ".o_documents_inspector_preview .o_document_preview", 2);
            let previews = target.querySelectorAll(
                ".o_documents_inspector_preview .o_document_preview img"
            );
            assert.equal(
                previews[0].dataset.src,
                "/documents/image/1/120x130?field=thumbnail&unique="
            );
            assert.equal(
                previews[1].dataset.src,
                "/documents/image/2/120x130?field=thumbnail&unique="
            );
            await click(target, ".o_kanban_record:nth-of-type(3) .o_record_selector");
            assert.containsN(target, ".o_documents_inspector_preview .o_document_preview", 3);
            previews = target.querySelectorAll(
                ".o_documents_inspector_preview .o_document_preview img"
            );
            assert.equal(
                previews[0].dataset.src,
                "/documents/image/1/120x75?field=thumbnail&unique="
            );
            assert.equal(
                previews[1].dataset.src,
                "/documents/image/2/120x75?field=thumbnail&unique="
            );
            assert.equal(
                previews[2].dataset.src,
                "/documents/image/3/120x75?field=thumbnail&unique="
            );
        });

        QUnit.test(
            "open xlsx converts to o-spreadsheet, clone it and opens the spreadsheet",
            async function (assert) {
                const spreadsheetCopyId = 99;
                const pyEnv = await startServer();
                const spreadsheetId = pyEnv["documents.document"].create([
                    {
                        name: "My excel file",
                        mimetype: XLSX_MIME_TYPES[0],
                        thumbnail_status: "present",
                    },
                ]);
                const serverData = {
                    views: {
                        "documents.document,false,kanban": `
                            <kanban js_class="documents_kanban">
                                <templates>
                                    <t t-name="kanban-box">
                                        <div>
                                            <div name="document_preview" class="o_kanban_image_wrapper">a thumbnail</div>
                                            <i class="fa fa-circle-thin o_record_selector"/>
                                            <field name="name"/>
                                            <field name="handler"/>
                                        </div>
                                    </t>
                                </templates>
                            </kanban>
                        `,
                        "documents.document,false,search": getEnrichedSearchArch(),
                    },
                };
                const { env, openView } = await start({
                    mockRPC: async (route, args) => {
                        if (args.method === "clone_xlsx_into_spreadsheet") {
                            assert.step("spreadsheet_cloned", "it should clone the spreadsheet");
                            assert.strictEqual(args.model, "documents.document");
                            assert.deepEqual(args.args, [spreadsheetId]);
                            return spreadsheetCopyId;
                        }
                    },
                    serverData,
                });
                await openView({
                    res_model: "documents.document",
                    views: [[false, "kanban"]],
                });
                mockActionService(env, (action) => {
                    assert.step(action.tag, "it should open the spreadsheet");
                    assert.deepEqual(action.params.spreadsheet_id, spreadsheetCopyId);
                });
                const fixture = getFixture();
                await click(fixture, ".oe_kanban_previewer");

                // confirm conversion to o-spreadsheet
                await click(fixture, ".modal-content .btn.btn-primary");
                assert.verifySteps(["spreadsheet_cloned", "action_open_spreadsheet"]);
            }
        );

        QUnit.test(
            "open WPS-marked xlsx converts to o-spreadsheet, clone it and opens the spreadsheet",
            async function (assert) {
                const spreadsheetCopyId = 99;
                const pyEnv = await startServer();
                const spreadsheetId = pyEnv["documents.document"].create([
                    {
                        name: "My excel file",
                        mimetype: XLSX_MIME_TYPES[1],
                        thumbnail_status: "present",
                    },
                ]);
                const serverData = {
                    views: {
                        "documents.document,false,kanban": `
                            <kanban js_class="documents_kanban">
                                <templates>
                                    <t t-name="kanban-box">
                                        <div>
                                            <div name="document_preview" class="o_kanban_image_wrapper">a thumbnail</div>
                                            <i class="fa fa-circle-thin o_record_selector"/>
                                            <field name="name"/>
                                            <field name="handler"/>
                                        </div>
                                    </t>
                                </templates>
                            </kanban>
                        `,
                        "documents.document,false,search": getEnrichedSearchArch(),
                    },
                };
                const { env, openView } = await start({
                    mockRPC: async (route, args) => {
                        if (args.method === "clone_xlsx_into_spreadsheet") {
                            assert.step("spreadsheet_cloned", "it should clone the spreadsheet");
                            assert.strictEqual(args.model, "documents.document");
                            assert.deepEqual(args.args, [spreadsheetId]);
                            return spreadsheetCopyId;
                        }
                    },
                    serverData,
                });
                await openView({
                    res_model: "documents.document",
                    views: [[false, "kanban"]],
                });
                mockActionService(env, (action) => {
                    assert.step(action.tag, "it should open the spreadsheet");
                    assert.deepEqual(action.params.spreadsheet_id, spreadsheetCopyId);
                });
                const fixture = getFixture();
                await click(fixture, ".oe_kanban_previewer");

                // confirm conversion to o-spreadsheet
                await click(fixture, ".modal-content .btn.btn-primary");
                assert.verifySteps(["spreadsheet_cloned", "action_open_spreadsheet"]);
            }
        );

        QUnit.test(
            "download spreadsheet document while selecting requested document",
            async function (assert) {
                assert.expect(1);
                const pyEnv = await startServer();
                const documentsFolderId1 = pyEnv["documents.folder"].create({
                    display_name: "Workspace1",
                    has_write_access: true,
                });
                pyEnv["documents.document"].create([
                    {
                        name: "My spreadsheet",
                        raw: "{}",
                        is_favorited: false,
                        folder_id: documentsFolderId1,
                        handler: "spreadsheet",
                    },
                    {
                        name: "Request",
                        folder_id: documentsFolderId1,
                        type: "empty",
                    },
                ]);
                const serverData = {
                    views: {
                        "documents.document,false,kanban": `
                            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                                <div>
                                    <i class="fa fa-circle-thin o_record_selector"/>
                                    <field name="name"/>
                                    <field name="handler"/>
                                </div>
                            </t></templates></kanban>
                        `,
                        "documents.document,false,search": getEnrichedSearchArch(),
                    },
                };
                const { openView } = await start({
                    serverData,
                });
                await openView({
                    res_model: "documents.document",
                    views: [[false, "kanban"]],
                });
                await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
                await click(target, ".o_kanban_record:nth-of-type(2) .o_record_selector");
                await click(target, "button.o_inspector_download");
                await contains(".o_notification", {
                    text: "Spreadsheets mass download not yet supported.\n Download spreadsheets individually instead.",
                });
            }
        );

        QUnit.test(
            "can open spreadsheet while multiple documents are selected along with it",
            async function (assert) {
                assert.expect(3);
                const pyEnv = await startServer();
                const documentsFolderId = pyEnv["documents.folder"].create({
                    display_name: "demo-workspace",
                    has_write_access: true,
                });
                pyEnv["documents.document"].create([
                    {
                        name: "test-spreadsheet",
                        raw: "{}",
                        folder_id: documentsFolderId,
                        handler: "spreadsheet",
                        thumbnail_status: "present",
                    },
                    {
                        folder_id: documentsFolderId,
                        mimetype: "image/png",
                        name: "test-image-1",
                    },
                    {
                        folder_id: documentsFolderId,
                        mimetype: "image/png",
                        name: "test-image-2",
                    },
                ]);
                const views = {
                    "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                            <templates>
                                <t t-name="kanban-box">
                                    <div>
                                        <div name="document_preview" class="o_kanban_image_wrapper">THUMBNAIL</div>
                                        <i class="fa fa-circle-thin o_record_selector"/>
                                        <field name="name"/>
                                        <field name="handler"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>`,
                };
                const { env, openView } = await createDocumentsViewWithMessaging({
                    hasWebClient: true,
                    serverData: { views },
                });
                await openView({
                    res_model: "documents.document",
                    views: [[false, "kanban"]],
                });
                patchWithCleanup(env.services.action, {
                    doAction(action) {
                        assert.step(action.tag);
                    },
                });
                const fixture = getFixture();
                const records = fixture.querySelectorAll(".o_kanban_record");
                await click(records[0], ".o_record_selector");
                await click(records[1], ".o_record_selector");
                await click(records[2], ".o_record_selector");
                await click(fixture.querySelector(".oe_kanban_previewer"));
                assert.containsNone(target, ".o_AttachmentViewer");
                assert.verifySteps(["action_open_spreadsheet"]);
            }
        );
    }
);
