/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { createDocumentsViewWithMessaging, loadServices } from "./documents_test_utils";

import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { DocumentsListRenderer } from "@documents/views/list/documents_list_renderer";

let target;

QUnit.module("documents", {}, function () {
    QUnit.module(
        "documents_kanban_mobile_tests.js",
        {
            async beforeEach() {
                setupViewRegistries();
                loadServices();

                target = getFixture();

                patchWithCleanup(DocumentsListRenderer, {
                    init() {
                        super.init(...arguments);
                        this.LONG_TOUCH_THRESHOLD = 0;
                    },
                });
            },
        },
        function () {
            QUnit.module("DocumentsKanbanViewMobile", function () {
                QUnit.skip("basic rendering on mobile", async function (assert) {
                    assert.expect(15);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.document"].create({
                        type: "folder",
                        access_internal: "edit",
                        name: "Workspace1",
                        description: "_F1-test-description_",
                    });
                    pyEnv["documents.document"].create([
                        {
                            folder_id: documentsFolderId1,
                            name: "gnap",
                        },
                        {
                            folder_id: documentsFolderId1,
                            name: "yop",
                        },
                    ]);
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="card" class="flex-row">
                            <i class="fa fa-circle mt-1 o_record_selector"/>
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    assert.containsOnce(
                        target,
                        ".o_documents_kanban_view",
                        "should have a documents kanban view"
                    );
                    assert.containsOnce(
                        target,
                        ".o_documents_inspector",
                        "should have a documents inspector"
                    );

                    const controlPanelButtons = target.querySelector(
                        ".o_control_panel .o_cp_buttons"
                    );
                    assert.containsOnce(
                        controlPanelButtons,
                        "> .btn",
                        "there should be one button left (Share) in the ControlPanel's left part"
                    );

                    let searchPanel = document.querySelector(".o_search_panel");
                    await click(searchPanel, ".o-dropdown:first-child");
                    await click(target, ".o_search_panel_category_value:nth-of-type(1) header");
                    assert.strictEqual(
                        searchPanel.querySelector(".o-dropdown:first-child").textContent,
                        "Workspace"
                    );
                    assert.ok(
                        target.querySelector(".o_documents_kanban_upload").disabled,
                        "the upload button should be disabled on global view"
                    );

                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be enabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be enabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_workspace"),
                        "the workspace button should only be visible for documents manager on global view"
                    );

                    await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
                    assert.ok(
                        target.querySelector(".o_documents_kanban_share_domain").disabled === false,
                        "the share button should be enabled on global view when documents are selected"
                    );

                    // select first folder
                    searchPanel = document.querySelector(".o_search_panel");
                    await click(searchPanel, ".o-dropdown:first-child");
                    await click(target, ".o_search_panel_category_value:nth-of-type(2) header");
                    assert.strictEqual(
                        searchPanel.querySelector(".o-dropdown:first-child").textContent,
                        "Workspace1"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_upload").disabled,
                        "the upload button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_workspace"),
                        "the workspace button should only be visible for documents manager"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_share_domain").disabled,
                        "the share button should be enabled when a folder is selected"
                    );
                });

                QUnit.module("DocumentsInspector");

                QUnit.skip("toggle inspector based on selection", async function (assert) {
                    assert.expect(13);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.document"].create({
                        name: "Workspace1",
                        description: "_F1-test-description_",
                        type: "folder",
                        access_internal: "view",
                    });
                    pyEnv["documents.document"].create([
                        { folder_id: documentsFolderId1 },
                        { folder_id: documentsFolderId1 },
                    ]);
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="card" class="flex-row">
                            <i class="fa fa-circle mt-1 o_record_selector"/>
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    assert.isNotVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be hidden when selection is empty"
                    );
                    assert.containsN(
                        document.body,
                        ".o_kanban_record:not(.o_kanban_ghost)",
                        2,
                        "should have 2 records in the renderer"
                    );

                    // select a first record
                    await click(document.querySelector(".o_kanban_record .o_record_selector"));
                    assert.containsOnce(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        "should have 1 record selected"
                    );
                    const toggleInspectorSelector =
                        ".o_documents_mobile_inspector > .o_documents_toggle_inspector";
                    assert.isVisible(
                        document.querySelector(toggleInspectorSelector),
                        "toggle inspector's button should be displayed when selection is not empty"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );

                    assert.isVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be opened"
                    );

                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.isNotVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be closed"
                    );

                    // select a second record
                    await click(
                        document.querySelectorAll(".o_kanban_record .o_record_selector")[1]
                    );
                    await nextTick();
                    assert.containsN(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        2,
                        "should have 2 records selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "2 documents selected"
                    );

                    // click on the record
                    await click(document.querySelector(".o_kanban_record"));
                    await nextTick();
                    assert.containsOnce(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        "should have 1 record selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );
                    assert.isVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be opened"
                    );

                    // close inspector
                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.containsOnce(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        "should still have 1 record selected after closing inspector"
                    );
                });
            });

            QUnit.module("DocumentsListViewMobile", function () {
                QUnit.skip("basic rendering on mobile", async function (assert) {
                    assert.expect(15);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.document"].create({
                        name: "Workspace1",
                        description: "_F1-test-description_",
                        type: "folder",
                        access_internal: "edit",
                    });
                    pyEnv["documents.document"].create([
                        {
                            folder_id: documentsFolderId1,
                            name: "gnap",
                        },
                        {
                            folder_id: documentsFolderId1,
                            name: "yop",
                        },
                    ]);
                    const views = {
                        "documents.document,false,list": `
                        <list js_class="documents_list">
                            <field name="name"/>
                        </list>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "list"]],
                    });

                    assert.containsOnce(
                        target,
                        ".o_documents_list_view",
                        "should have a documents kanban view"
                    );
                    assert.containsOnce(
                        target,
                        ".o_documents_inspector",
                        "should have a documents inspector"
                    );

                    const controlPanelButtons = target.querySelector(
                        ".o_control_panel .o_cp_buttons"
                    );
                    assert.containsOnce(
                        controlPanelButtons,
                        "> .btn",
                        "there should be one button left (Share) in the ControlPanel's left part"
                    );
                    let searchPanel = document.querySelector(".o_search_panel");
                    await click(searchPanel, ".o-dropdown:first-child");
                    await click(target, ".o_search_panel_category_value:nth-of-type(1) header");
                    assert.strictEqual(
                        searchPanel.querySelector(".o-dropdown:first-child").textContent,
                        "Workspace"
                    );
                    assert.ok(
                        target.querySelector(".o_documents_kanban_upload").disabled,
                        "the upload button should be disabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be disabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be disabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_workspace"),
                        "the workspace button should only be visible for documents manager on global view"
                    );

                    await click(target, ".o_data_row:nth-of-type(1) .o_list_record_selector");
                    assert.ok(
                        target.querySelector(".o_documents_kanban_share_domain").disabled === false,
                        "the share button should be enabled on global view when documents are selected"
                    );

                    // select first folder
                    searchPanel = document.querySelector(".o_search_panel");
                    await click(searchPanel, ".o-dropdown:first-child");
                    await click(target, ".o_search_panel_category_value:nth-of-type(2) header");
                    assert.strictEqual(
                        searchPanel.querySelector(".o-dropdown:first-child").textContent,
                        "Workspace1"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_upload").disabled,
                        "the upload button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_workspace"),
                        "the workspace button should only be visible for documents manager"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_share_domain").disabled,
                        "the share button should be enabled when a folder is selected"
                    );
                });

                QUnit.module("DocumentsInspector");

                QUnit.skip("toggle inspector based on selection", async function (assert) {
                    assert.expect(15);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.document"].create({
                        name: "Workspace1",
                        description: "_F1-test-description_",
                        type: "folder",
                        access_internal: "view",
                    });
                    pyEnv["documents.document"].create([
                        { folder_id: documentsFolderId1 },
                        { folder_id: documentsFolderId1 },
                    ]);
                    const views = {
                        "documents.document,false,list": `<list js_class="documents_list">
                    <field name="name"/>
                </list>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        touchScreen: true,
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "list"]],
                    });

                    assert.isNotVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be hidden when selection is empty"
                    );
                    assert.containsN(
                        document.body,
                        ".o_data_row",
                        2,
                        "should have 2 records in the renderer"
                    );

                    // select a first record (enter selection mode)
                    await click(document.querySelector(".o_data_row"));
                    const toggleInspectorSelector =
                        ".o_documents_mobile_inspector > .o_documents_toggle_inspector";
                    assert.isVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should be opened"
                    );

                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.isNotVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should be closed"
                    );

                    assert.isVisible(
                        document.querySelector(toggleInspectorSelector),
                        "toggle inspector's button should be displayed when selection is not empty"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );
                    assert.containsOnce(
                        document.body,
                        ".o_data_row.o_data_row_selected",
                        "should have 1 record selected"
                    );

                    // select a second record
                    await click(document.querySelector(".o_data_row:nth-child(2)"));
                    assert.containsN(
                        document.body,
                        ".o_data_row.o_data_row_selected",
                        2,
                        "should have 2 records selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "2 documents selected"
                    );
                    assert.isNotVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should stay closed"
                    );

                    // disable selection mode
                    await click(document.querySelector(".o_list_unselect_all"));
                    assert.containsNone(
                        document.body,
                        ".o_document_list_record.o_data_row_selected",
                        "shouldn't have record selected"
                    );

                    // click on the record
                    await click(document.querySelector(".o_data_row"));
                    assert.containsOnce(
                        document.body,
                        ".o_data_row.o_data_row_selected",
                        "should have 1 record selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );
                    assert.isVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should be opened"
                    );

                    // close inspector
                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.containsOnce(
                        document.body,
                        ".o_data_row .o_list_record_selector input:checked",
                        "should still have 1 record selected after closing inspector"
                    );
                });
            });
        }
    );
});
