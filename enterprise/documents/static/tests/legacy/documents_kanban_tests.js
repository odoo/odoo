/* @odoo-module */

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { DocumentsKanbanRenderer } from "@documents/views/kanban/documents_kanban_renderer";
import {
    createDocumentsView as originalCreateDocumentsView,
    createDocumentsViewWithMessaging,
    loadServices,
} from "./documents_test_utils";
import * as dsHelpers from "@web/../tests/core/domain_selector_tests";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";

import {
    toggleMenuItem,
    toggleSearchBarMenu,
    pagerNext,
    pagerPrevious,
} from "@web/../tests/search/helpers";
import testUtils from "@web/../tests/legacy_tests/helpers/test_utils";
import {
    click as legacyClick,
    editInput,
    clickOpenedDropdownItem,
    clickOpenM2ODropdown,
    dragAndDrop,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { browser, makeRAMLocalStorage } from "@web/core/browser/browser";
import { serializeDate } from "@web/core/l10n/dates";
import { router } from "@web/core/browser/router";
import {
    click,
    contains,
    dragoverFiles,
    dropFiles,
    inputFiles,
    insertText,
} from "@web/../tests/utils";

const { DateTime } = luxon;

function createDocumentsView(params) {
    return originalCreateDocumentsView({
        serverData: { models: pyEnv.getData(), views: {} },
        ...params,
    });
}

let target;
let pyEnv;

QUnit.module("documents", {}, function () {
    QUnit.module(
        "documents_kanban_tests.js",
        {
            async beforeEach() {
                loadServices();
                patchWithCleanup(browser, {
                    navigator: {
                        ...browser.navigator,
                        clipboard: {
                            writeText: () => {},
                        },
                    },
                });
                this.ORIGINAL_CREATE_XHR = fileUploadService.createXhr;
                this.patchDocumentXHR = (mockedXHRs, customSend) => {
                    fileUploadService.createXhr = () => {
                        const xhr = new window.EventTarget();
                        Object.assign(xhr, {
                            upload: new window.EventTarget(),
                            open() {},
                            send(data) {
                                customSend && customSend(data);
                            },
                        });
                        mockedXHRs.push(xhr);
                        return xhr;
                    };
                };
                pyEnv = await startServer();
                const resPartnerIds = pyEnv["res.partner"].create([
                    { display_name: "Hazard" },
                    { display_name: "Lukaku" },
                    { display_name: "De Bruyne" },
                    { email: "raoul@grosbedon.fr", name: "Raoul Grosbedon" },
                    { email: "raoulette@grosbedon.fr", name: "Raoulette Grosbedon" },
                ]);
                const resUsersIds = pyEnv["res.users"].create([
                    {
                        display_name: "Hazard",
                        partner_id: resPartnerIds[0],
                        login: "hazard",
                        password: "hazard",
                    },
                    { display_name: "Lukaku", partner_id: resPartnerIds[1] },
                    { display_name: "De Bruyne", partner_id: resPartnerIds[2] },
                ]);
                const documentsFolderIds = pyEnv["documents.document"].create([
                    { name: "Workspace1", type: "folder", access_internal: "edit", user_permission: "edit", is_pinned_folder: true, folder_id: false, owner_id: 1 },
                    { name: "Workspace2", type: "folder", access_internal: "edit", user_permission: "edit", is_pinned_folder: true, folder_id: false, owner_id: 1 },
                ]);
                documentsFolderIds.push(
                    pyEnv["documents.document"].create([
                        {
                            name: "Workspace3",
                            folder_id: documentsFolderIds[0],
                            type: "folder",
                            access_internal: "edit",
                            user_permission: "edit",
                        },
                    ])
                );
                const documentsTagIds = pyEnv["documents.tag"].create([
                    { display_name: "New", sequence: 11 },
                    { display_name: "Draft", sequence: 10 },
                    { display_name: "No stress", sequence: 10 },
                ]);
                const documentsEmbeddedActions = [];
                const resFakeIds = pyEnv["res.fake"].create([{ name: "fake1" }, { name: "fake2" }]);
                const irAttachmentId1 = pyEnv["ir.attachment"].create({});
                const [documentsDocumentId1, documentsDocumentId2] = pyEnv[
                    "documents.document"
                ].create([
                    {
                        activity_state: "today",
                        available_embedded_actions_ids: documentsEmbeddedActions,
                        file_size: 30000,
                        folder_id: documentsFolderIds[0],
                        is_editable_attachment: true,
                        name: "yop",
                        owner_id: resUsersIds[0],
                        partner_id: resPartnerIds[1],
                        res_id: resFakeIds[0],
                        res_model: "res.fake",
                        res_model_name: "Task",
                        res_name: "Write specs",
                        tag_ids: [documentsTagIds[0], documentsTagIds[1]],
                    },
                    {
                        attachment_id: pyEnv["ir.attachment"].create({}),
                        available_embedded_actions_ids: documentsEmbeddedActions,
                        file_size: 20000,
                        folder_id: documentsFolderIds[0],
                        mimetype: "application/pdf",
                        name: "blip",
                        owner_id: resUsersIds[1],
                        partner_id: resPartnerIds[1],
                        res_id: resFakeIds[1],
                        res_model: "res.fake",
                        res_model_name: "Task",
                        res_name: "Write tests",
                        tag_ids: [documentsTagIds[1]],
                    },
                ]);
                pyEnv["documents.document"].create([
                    {
                        available_embedded_actions_ids: documentsEmbeddedActions,
                        file_size: 15000,
                        folder_id: documentsFolderIds[0],
                        lock_uid: resUsersIds[2],
                        name: "gnap",
                        owner_id: resUsersIds[1],
                        partner_id: resPartnerIds[0],
                        res_id: documentsDocumentId2,
                        res_model: "documents.document",
                        res_model_name: "Task",
                        tag_ids: [documentsTagIds[0], documentsTagIds[1], documentsTagIds[2]],
                    },
                    {
                        available_embedded_actions_ids: documentsEmbeddedActions,
                        file_size: 10000,
                        folder_id: documentsFolderIds[0],
                        mimetype: "image/png",
                        name: "burp",
                        owner_id: resUsersIds[0],
                        partner_id: resPartnerIds[2],
                        res_id: irAttachmentId1,
                        res_model: "ir.attachment",
                        res_model_name: "Attachment",
                    },
                    {
                        available_embedded_actions_ids: documentsEmbeddedActions,
                        file_size: 40000,
                        folder_id: documentsFolderIds[0],
                        lock_uid: resUsersIds[0],
                        name: "zip",
                        owner_id: resUsersIds[1],
                        partner_id: resPartnerIds[1],
                        tag_ids: documentsTagIds,
                    },
                    {
                        available_embedded_actions_ids: [],
                        file_size: 70000,
                        folder_id: documentsFolderIds[1],
                        name: "pom",
                        owner_id:  resUsersIds[0],
                        partner_id: resPartnerIds[2],
                        res_id: documentsDocumentId1,
                        res_model: "documents.document",
                        res_model_name: "Document",
                    },
                    {
                        active: false,
                        file_size: 70000,
                        available_embedded_actions_ids: [],
                        folder_id: documentsFolderIds[0],
                        name: "wip",
                        owner_id: resUsersIds[2],
                        partner_id: resPartnerIds[2],
                        res_id: irAttachmentId1,
                        res_model: "ir.attachment",
                        res_model_name: "Attachment",
                    },
                    {
                        active: false,
                        available_embedded_actions_ids: [],
                        file_size: 20000,
                        folder_id: documentsFolderIds[0],
                        mimetype: "text/plain",
                        name: "zorro",
                        owner_id: resUsersIds[2],
                        partner_id: resPartnerIds[2],
                    },
                ]);
                setupViewRegistries();
                target = getFixture();
            },
            afterEach() {
                fileUploadService.createXhr = this.ORIGINAL_CREATE_XHR;
                pyEnv = undefined;
            },
        },
        function () {
            QUnit.skip("kanban basic rendering", async function (assert) {
                assert.expect(30);
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                });
                assert.strictEqual(
                    target
                        .querySelector(
                            "header.active > .o_search_panel_label .o_search_panel_label_title"
                        )
                        .textContent.trim(),
                    "Workspace1",
                    "the first selected record should be the first folder"
                );
                assert.strictEqual(
                    target
                        .querySelector("header.active > .o_search_panel_counter")
                        .textContent.trim(),
                    "5",
                    "the first folder should have 5 as counter"
                );
                assert.containsOnce(
                    target,
                    ".o_search_panel_category_value:contains(All) header",
                    "Should only have a single all selector"
                );

                await legacyClick(target, ".o_search_panel_category_value:nth-of-type(1) header");

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

                await legacyClick(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
                assert.ok(
                    target.querySelector(".o_documents_kanban_share_domain").disabled === false,
                    "the share button should be enabled on global view when documents are selected"
                );

                assert.containsN(
                    target,
                    ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                    6,
                    "should have 6 records in the renderer"
                );
                assert.containsNone(
                    target,
                    ".o_documents_selector_tags",
                    "should not display the tag navigation because no workspace is selected by default"
                );

                await legacyClick(target, ".o_search_panel_category_value:nth-of-type(2) header");

                // check view layout
                assert.containsOnce(target, ".o_content > div.o_search_panel");
                assert.containsOnce(target, ".o_content > div.o_kanban_renderer");
                assert.containsOnce(target, ".o_content > div.o_documents_inspector");
                assert.containsOnce(
                    target.querySelector(".o_content"),
                    "> div.o_search_panel",
                    "should have a 'documents selector' column"
                );
                assert.containsOnce(
                    target,
                    ".o_content > .o_kanban_renderer",
                    "should have a 'classical kanban view' column"
                );
                assert.hasClass(
                    target.querySelector(".o_kanban_view"),
                    "o_documents_kanban_view",
                    "should have classname 'o_documents_kanban_view'"
                );
                assert.containsN(
                    target,
                    ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                    5,
                    "should have 5 records in the renderer"
                );
                assert.containsOnce(
                    target,
                    ".o_kanban_record:first .o_record_selector",
                    "should have a 'selected' button"
                );
                assert.containsOnce(
                    target,
                    ".o_content > .o_documents_inspector",
                    "should have a 'document inspector' column"
                );

                // check control panel buttons
                assert.containsOnce(
                    target,
                    ".o_cp_buttons .btn-primary.dropdown-toggle:visible"
                );
                assert.strictEqual(
                    $(".o_cp_buttons .btn-primary.dropdown-toggle:visible")
                        .get(0)
                        .textContent.trim(),
                    "New",
                    "should have a primary 'New' button"
                );
                assert.ok(
                    target.querySelector(".o_documents_kanban_upload").disabled === false,
                    "the upload button should be enabled when a folder is selected"
                );
                assert.containsOnce(
                    target,
                    ".o_cp_buttons button.o_documents_kanban_url",
                    "should allow to save a URL on small / xl screen"
                );
                assert.ok(
                    target.querySelector(".o_documents_kanban_url").disabled === false,
                    "the upload url button should be enabled when a folder is selected"
                );
                assert.strictEqual(
                    target
                        .querySelector(".o_cp_buttons button.o_documents_kanban_request")
                        .textContent.trim(),
                    "Request",
                    "should have a primary 'request' button"
                );
                assert.ok(
                    target.querySelector(".o_documents_kanban_request").disabled === false,
                    "the request button should be enabled when a folder is selected"
                );
                assert.containsOnce(
                    target,
                    ".o_cp_buttons .btn-secondary:visible"
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_cp_buttons .o_documents_kanban_share_domain"
                        )
                        .textContent.trim(),
                    "Share",
                    "should have a secondary 'Share' button"
                );
                assert.ok(
                    target.querySelector(".o_documents_kanban_share_domain").disabled === false,
                    "the share button should be enabled when a folder is selected"
                );
                await legacyClick(target, ".o_search_panel_category_value[title='Trash'] header");
                assert.ok(
                    target.querySelector(".o_documents_kanban_upload").disabled,
                    "the upload button should be disabled inside TRASH folder."
                );
            });

            QUnit.skip(
                "can select records by clicking on the select icon",
                async function (assert) {
                    assert.expect(6);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                </t></templates></kanban>`,
                    });

                    const firstRecord = target.querySelector(".o_kanban_record");
                    assert.doesNotHaveClass(
                        firstRecord,
                        "o_record_selected",
                        "first record should not be selected"
                    );
                    await legacyClick(firstRecord, ".o_record_selector");
                    assert.hasClass(
                        firstRecord,
                        "o_record_selected",
                        "first record should be selected"
                    );

                    const thirdRecord = target.querySelectorAll(".o_kanban_record")[2];
                    assert.doesNotHaveClass(
                        thirdRecord,
                        "o_record_selected",
                        "third record should not be selected"
                    );
                    await legacyClick(thirdRecord, ".o_record_selector");
                    assert.hasClass(
                        thirdRecord,
                        "o_record_selected",
                        "third record should be selected"
                    );

                    await legacyClick(firstRecord, ".o_record_selector");
                    assert.doesNotHaveClass(
                        firstRecord,
                        "o_record_selected",
                        "first record should not be selected"
                    );
                    assert.hasClass(
                        thirdRecord,
                        "o_record_selected",
                        "third record should be selected"
                    );
                }
            );

            QUnit.skip("can select records by clicking on them", async function (assert) {
                assert.expect(5);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                    </t></templates></kanban>`,
                });

                assert.containsNone(
                    target,
                    ".o_kanban_record.o_record_selected",
                    "no record should be selected"
                );

                const firstRecord = target.querySelector(".o_kanban_record");
                await legacyClick(firstRecord);
                assert.containsOnce(
                    target,
                    ".o_kanban_record.o_record_selected",
                    "one record should be selected"
                );
                assert.hasClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should be selected"
                );

                const thirdRecord = target.querySelectorAll(".o_kanban_record")[2];
                await legacyClick(thirdRecord);
                assert.containsOnce(
                    target,
                    ".o_kanban_record.o_record_selected",
                    "one record should be selected"
                );
                assert.hasClass(
                    thirdRecord,
                    "o_record_selected",
                    "third record should be selected"
                );
            });

            QUnit.skip("can unselect a record", async function () {
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                    </t></templates></kanban>`,
                });
                await contains(".o_kanban_record", { count: 11 });
                await contains(".o_kanban_record.o_record_selected", { count: 0 });
                await click(":nth-child(1 of .o_kanban_record)");
                await contains(".o_kanban_record.o_record_selected");
                await click(":nth-child(1 of .o_kanban_record)");
                await contains(".o_kanban_record.o_record_selected", { count: 0 });
            });

            QUnit.skip("can select records with keyboard navigation", async function (assert) {
                assert.expect(4);

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <div>
                        <field name="name"/>
                        <button name="some_method" type="object"/>
                    </div>
                    </t></templates></kanban>`,
                });

                patchWithCleanup(kanban.env.services.action, {
                    doActionButton({ onClose }) {
                        assert.ok(false, "should not trigger an 'execute_action' event");
                        onClose();
                    },
                });

                const firstRecord = target.querySelector(".o_kanban_record");
                assert.doesNotHaveClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should not be selected"
                );
                await triggerEvent(firstRecord, null, "keydown", {
                    key: "Enter",
                });
                assert.hasClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should be selected"
                );

                const thirdRecord = target.querySelector(".o_kanban_record:nth-of-type(3)");
                await triggerEvent(thirdRecord, null, "keydown", {
                    key: "Enter",
                });
                assert.hasClass(
                    thirdRecord,
                    "o_record_selected",
                    "third record should be selected"
                );
                assert.doesNotHaveClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should no longer be selected"
                );
            });

            QUnit.skip("can multi select records with shift and ctrl", async function (assert) {
                assert.expect(6);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <div>
                        <field name="name"/>
                        <button name="some_method" type="object"/>
                    </div>
                </t></templates></kanban>`,
                });

                const firstRecord = target.querySelector(".o_kanban_record");
                assert.doesNotHaveClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should not be selected"
                );
                await triggerEvent(firstRecord, null, "keydown", {
                    key: "Enter",
                });
                assert.hasClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should be selected"
                );

                const thirdRecord = target.querySelectorAll(".o_kanban_record")[2];
                await triggerEvent(thirdRecord, null, "keydown", {
                    key: "Enter",
                    shiftKey: true,
                });
                assert.hasClass(
                    thirdRecord,
                    "o_record_selected",
                    "third record should be selected (shift)"
                );
                assert.hasClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should still be selected (shift)"
                );

                await triggerEvent(firstRecord, null, "keydown", {
                    key: "Enter",
                    ctrlKey: true,
                });

                assert.hasClass(
                    thirdRecord,
                    "o_record_selected",
                    "third record should still be selected (ctrl)"
                );
                assert.doesNotHaveClass(
                    firstRecord,
                    "o_record_selected",
                    "first record should no longer be selected (ctrl)"
                );
            });

            QUnit.skip("can multi edit records", async function (assert) {
                assert.expect(6);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                        <kanban js_class="documents_kanban"><templates><t t-name="card">
                            <div class="d-flex">
                                <i class="fa fa-circle mt-1 o_record_selector"/>
                                <field name="name"/>
                                <field name="is_editable_attachment" widget="boolean_toggle"/>
                            </div>
                        </t></templates></kanban>`,
                    mockRPC(route, args) {
                        if (args.method === "write") {
                            assert.deepEqual(args.args, [[4, 5], { is_editable_attachment: true }]);
                        }
                    },
                });

                assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 5);
                assert.containsNone(target, ".o_record_selected");
                assert.containsOnce(
                    target,
                    ".o_field_widget[name=is_editable_attachment] input:checked"
                );
                await legacyClick(target.querySelectorAll(".o_record_selector")[3]);
                await legacyClick(target.querySelectorAll(".o_record_selector")[4]);
                assert.containsN(target, ".o_record_selected", 2);
                await legacyClick(
                    target.querySelectorAll(".o_field_widget[name=is_editable_attachment] input")[4]
                );
                await nextTick();
                assert.containsN(
                    target,
                    ".o_field_widget[name=is_editable_attachment] input:checked",
                    3
                );
            });

            QUnit.skip(
                "only visible selected records are kept after a reload",
                async function (assert) {
                    assert.expect(6);

                    const kanban = await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch:
                            '<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">' +
                            '<i class="fa fa-circle mt-1 o_record_selector"/>' +
                            '<field name="name"/>' +
                            '<button name="some_method" type="object"/>' +
                            "</t></templates></kanban>",
                        searchViewArch: `
                    <search>
                        <filter name="owo" string="OwO" domain="[['name', '=', 'burp']]"/>
                    </search>`,
                    });

                    kanban.model.root.records
                        .filter((rec) => ["yop", "burp", "blip"].includes(rec.data.name))
                        .forEach((rec) => rec.toggleSelection(true));
                    await nextTick();

                    assert.containsN(
                        target,
                        ".o_record_selected",
                        3,
                        "should have 3 selected records"
                    );
                    assert.containsN(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        3,
                        "should show 3 document previews in the DocumentsInspector"
                    );

                    await toggleSearchBarMenu(target);
                    await toggleMenuItem(target, "OwO");

                    assert.containsOnce(
                        target,
                        ".o_record_selected",
                        "should have 1 selected record"
                    );
                    assert.containsOnce(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        "should show 1 document preview in the DocumentsInspector"
                    );

                    await toggleMenuItem(target, "OwO");

                    assert.containsOnce(
                        target,
                        ".o_record_selected",
                        "should have 1 selected records"
                    );
                    assert.containsOnce(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        "should show 1 document previews in the DocumentsInspector"
                    );
                }
            );

            QUnit.skip(
                "selected records are kept when a button is clicked",
                async function (assert) {
                    assert.expect(6);

                    const kanban = await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                        <button name="some_method" type="object"/>
                </t></templates></kanban>`,
                    });

                    patchWithCleanup(kanban.env.services.action, {
                        doActionButton(ev) {
                            assert.strictEqual(
                                ev.name,
                                "some_method",
                                "should call the correct method"
                            );
                            pyEnv["documents.document"].write([ev.resId], { name: "yop changed" });
                            ev.onClose();
                        },
                    });

                    kanban.model.root.records
                        .filter((rec) => ["yop", "burp", "blip"].includes(rec.data.name))
                        .forEach((rec) => rec.toggleSelection(true));
                    await nextTick();

                    assert.containsN(
                        target,
                        ".o_record_selected",
                        3,
                        "should have 3 selected records"
                    );
                    assert.containsN(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        3,
                        "should show 3 document previews in the DocumentsInspector"
                    );

                    await legacyClick(
                        Array.from(target.querySelectorAll(".o_kanban_record button")).find(
                            (el) => el.parentElement.textContent.trim() === "yop"
                        )
                    );

                    assert.strictEqual(
                        Array.from(target.querySelectorAll(".o_record_selected")).filter(
                            (el) => el.textContent.trim() === "yop changed"
                        ).length,
                        1,
                        "should have re-rendered the updated record"
                    );
                    assert.containsN(
                        target,
                        ".o_record_selected",
                        3,
                        "should still have 3 selected records"
                    );
                    assert.containsN(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        3,
                        "should still show 3 document previews in the DocumentsInspector"
                    );
                }
            );

            QUnit.skip("can share current domain", async function (assert) {
                assert.expect(6);

                patchWithCleanup(navigator.clipboard, {
                    async writeText(text) {
                        assert.step("copy");
                    },
                });

                const [resUsersId1] = pyEnv["res.users"].search([["display_name", "=", "Lukaku"]]);
                const domain = ["owner_id", "=", resUsersId1];
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                    domain: [domain],
                    mockRPC: async function (route, args) {
                        if (args.method === "web_save") {
                            assert.step("web_save");
                            assert.deepEqual(args.kwargs.context, {
                                default_document_ids: false,
                                default_domain: [
                                    "&",
                                    domain,
                                    "&",
                                    ["folder_id", "child_of", 1],
                                    ["res_model", "in", ["res.fake"]],
                                ],
                                default_folder_id: 1,
                                default_tag_ids: [[6, false, []]],
                                default_type: "domain",
                                lang: "en",
                                tz: "taht",
                                uid: 2,
                            });
                        }
                    },
                });

                await legacyClick(
                    target.querySelectorAll(".o_search_panel_category_value header")[1]
                );
                // filter on 'task' in the DocumentsSelector
                await legacyClick($(target).find(".o_search_panel_label_title:contains(Task)")[0]);

                assert.containsN(
                    target,
                    ".o_kanban_record:not(.o_kanban_ghost)",
                    1,
                    "should have 2 records in the renderer"
                );

                await legacyClick($(".o_cp_buttons .dropdown-toggle:visible").get(0));
                await legacyClick($(".o_documents_kanban_share_domain:visible").get(0));
                assert.verifySteps([]);
                await legacyClick($(".o_form_button_save").get(0));
                assert.verifySteps(["web_save", "copy"]);
            });

            QUnit.skip("can upload from URL", async function (assert) {
                assert.expect(1);

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                patchWithCleanup(kanban.env.services.action, {
                    doAction(action) {
                        assert.deepEqual(
                            action,
                            "documents.action_url_form",
                            "should open the url form"
                        );
                    },
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                await legacyClick($(".o_cp_buttons .dropdown-toggle:visible").get(0));
                await legacyClick($(".o_documents_kanban_url:visible").get(0));
            });

            QUnit.skip("can Request a file", async function (assert) {
                assert.expect(1);

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                patchWithCleanup(kanban.env.services.action, {
                    doAction(action) {
                        assert.deepEqual(
                            action,
                            "documents.action_request_form",
                            "should open the url form"
                        );
                    },
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                await legacyClick($(".o_cp_buttons .dropdown-toggle:visible").get(0));
                await legacyClick($(".o_documents_kanban_request:visible").get(0));
            });

            QUnit.skip("can navigate with arrows", async function (assert) {
                assert.expect(10);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                });
                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(1) header")
                );
                // Force specific sizes for the test.
                // We will have rows of 2 cards each
                const kanbanEl = target.querySelector(".o_kanban_renderer");
                kanbanEl.style.maxWidth = "500px";
                const cards = kanbanEl.querySelectorAll(".o_kanban_record");
                for (const card of cards) {
                    card.style.width = "150px";
                }
                cards[0].focus();
                const triggerKey = async (key) => {
                    await triggerEvent(document.activeElement, null, "keydown", {
                        key,
                    });
                };
                await triggerKey("ArrowRight");
                assert.strictEqual(
                    document.activeElement,
                    cards[1],
                    "should have moved to the next card"
                );
                await triggerKey("ArrowDown");
                assert.strictEqual(
                    document.activeElement,
                    cards[3],
                    "should have moved to card below"
                );
                await triggerKey("ArrowLeft");
                assert.strictEqual(
                    document.activeElement,
                    cards[2],
                    "should have moved to the card on the left"
                );
                await triggerKey("ArrowLeft");
                assert.strictEqual(
                    document.activeElement,
                    cards[1],
                    "should have moved to the last card of the previous row"
                );
                await triggerKey("ArrowDown");
                assert.strictEqual(
                    document.activeElement,
                    cards[3],
                    "should have moved to card below"
                );
                await triggerKey("ArrowDown");
                assert.strictEqual(
                    document.activeElement,
                    cards[5],
                    "should have moved to card below"
                );
                await triggerKey("ArrowLeft");
                assert.strictEqual(
                    document.activeElement,
                    cards[4],
                    "should have moved to the card on the left"
                );
                await triggerKey("ArrowUp");
                assert.strictEqual(
                    document.activeElement,
                    cards[2],
                    "should have moved one row up"
                );
                await triggerKey("ArrowUp");
                assert.strictEqual(
                    document.activeElement,
                    cards[0],
                    "should have moved one row up"
                );
                await triggerKey("ArrowUp");
                assert.hasClass(
                    document.activeElement,
                    "o_searchview_input",
                    "should have moved to the search input"
                );
            });

            QUnit.skip("Preserve search domain when removing tags", async (assert) => {
                assert.expect(5);
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    domain: [["user_id", "!=", 299792458]],  // Add some filter to the domain
                    arch: `<kanban js_class="documents_kanban"><templates>
                        <t t-name="card">
                            <field name="name"/>
                        </t></templates></kanban>`,
                    mockRPC: function (route, args) {
                        if (route === "/web/dataset/call_kw/documents.document/web_search_read" && args.model === "documents.document"
                        ) {
                            assert.step(JSON.stringify(args.kwargs.domain || []));
                        }
                    },
                });
                await legacyClick($(target).find(".o_kanban_record:nth-child(1)")[0]);
                assert.containsN(target, ".o_inspector_tag", 2, "should display two tags");
                await legacyClick(target.querySelector(".o_inspector_tag:nth-of-type(2) .o_inspector_tag_remove"));
                assert.containsN(target, ".o_inspector_tag", 1, "One tag got should get removed");
                assert.verifySteps([
                    '["&",["user_id","!=",299792458],["folder_id","child_of",1]]',
                    '["&",["user_id","!=",299792458],["folder_id","child_of",1]]'
                ], "Search domain should be preserved when removing tags");
            });

            QUnit.module("DocumentsInspector");

            QUnit.skip("document inspector with no document selected", async function (assert) {
                assert.expect(3);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                assert.strictEqual(
                    target
                        .querySelector(".o_documents_inspector_preview")
                        .textContent.replace(/\s+/g, ""),
                    "_F1-test-description_",
                    "should display the current workspace description"
                );
                assert.strictEqual(
                    target.querySelectorAll(".o_inspector_value")[0].textContent.trim(),
                    "5",
                    "should display the correct number of documents"
                );
                assert.strictEqual(
                    target.querySelectorAll(".o_inspector_value")[1].textContent.trim(),
                    "0.12 MB",
                    "should display the correct size"
                );
            });

            QUnit.skip("can collapse and uncollapse document inspector", async function (assert) {
                assert.expect(21);

                const views = {
                    "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                <templates>
                    <t t-name="card" class="flex-row">
                        <i class="fa fa-circle-thin mt-1 o_record_selector"/>
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

                assert.containsOnce(target, ".o_documents_inspector_panel:visible");
                assert.containsOnce(target, ".o_documents_inspector_preview:visible");
                assert.containsOnce(target, ".o_documents_inspector_info:visible");

                // no records selected
                assert.containsOnce(target, ".o_inspector_button");
                assert.containsOnce(target, ".o_inspector_button[title=Fold]");

                // select a document record
                await legacyClick(target.querySelector(".o_kanban_record"));
                assert.deepEqual(
                    [...target.querySelectorAll(".o_inspector_button")].map((e) =>
                        e.getAttribute("title")
                    ),
                    [
                        "Fold",
                        "Download",
                        "Share this selection",
                        "Replace",
                        "Lock",
                        "Open chatter",
                        "Move to trash",
                    ]
                );

                // collapse documents inspector
                await legacyClick(target, ".o_documents_inspector_panel .o_inspector_toggle");
                assert.containsNone(target, ".o_documents_inspector_panel:visible");
                assert.containsNone(target, ".o_documents_inspector_preview:visible");
                assert.containsNone(target, ".o_documents_inspector_info:visible");
                assert.containsOnce(target, ".o_documents_inspector_sidebar:visible");
                assert.deepEqual(
                    [...target.querySelectorAll(".o_inspector_button")].map((e) =>
                        e.getAttribute("title")
                    ),
                    ["Unfold", "Open chatter"]
                );

                // open the chatter from inspector sidebar
                await legacyClick(target, ".o_documents_inspector .o_inspector_open_chatter");
                await contains(".o-mail-Chatter");
                assert.containsOnce(target, ".o_documents_inspector_sidebar:visible");
                assert.containsOnce(target, ".o_inspector_button");
                assert.containsOnce(target, ".o_inspector_button[title=Unfold]");

                // close the chatter
                await legacyClick(target, ".o-mail-Chatter-close");
                await contains(".o_document_chatter_container .o-mail-Chatter", { count: 0 });
                assert.deepEqual(
                    [...target.querySelectorAll(".o_inspector_button")].map((e) =>
                        e.getAttribute("title")
                    ),
                    ["Unfold", "Open chatter"]
                );

                // unselect document record

                await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);
                assert.containsOnce(target, ".o_inspector_button");
                assert.containsOnce(target, ".o_inspector_button[title=Unfold]");
                // uncollapse documents inspector
                await legacyClick(target, ".o_documents_inspector_sidebar .o_inspector_toggle");
                assert.containsOnce(target, ".o_documents_inspector_panel:visible");
                assert.containsNone(target, ".o_documents_inspector_sidebar:visible");
            });

            QUnit.skip("document inspector with selected documents", async function (assert) {
                assert.expect(5);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                // select a first document
                await legacyClick(
                    target.querySelector(".o_kanban_record:nth-of-type(1) .o_record_selector")
                );

                assert.containsNone(
                    target,
                    ".o_documents_inspector_info .o_selection_size",
                    "should not display the number of selected documents (because only 1)"
                );
                assert.containsOnce(
                    target,
                    ".o_documents_inspector_preview .o_document_preview",
                    "should show a preview of the selected document"
                );
                assert.hasClass(
                    target.querySelector(".o_documents_inspector_preview .o_document_preview"),
                    "o_documents_single_preview",
                    "should have the 'o_documents_single_preview' className"
                );

                // select a second document
                await legacyClick(
                    target.querySelector(".o_kanban_record:nth-of-type(2) .o_record_selector")
                );

                assert.strictEqual(
                    target
                        .querySelector(".o_documents_inspector_preview .o_selection_size")
                        .textContent.trim(),
                    "2 documents selected",
                    "should display the correct number of selected documents"
                );
                assert.containsN(
                    target,
                    ".o_documents_inspector_preview .o_document_preview",
                    2,
                    "should show a preview of the selected documents"
                );
            });

            QUnit.skip("document inspector limits preview to 4 documents", async function (assert) {
                assert.expect(2);

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                // select five documents
                for (let i = 0; i < 5; i++) {
                    kanban.model.root.records[i].toggleSelection(true);
                }
                await nextTick();

                assert.strictEqual(
                    target
                        .querySelector(".o_documents_inspector_preview .o_selection_size")
                        .textContent.trim(),
                    "5 documents selected",
                    "should display the correct number of selected documents"
                );
                assert.containsN(
                    target,
                    ".o_documents_inspector_preview .o_document_preview",
                    4,
                    "should only show a preview of 4 selected documents"
                );
            });

            QUnit.skip(
                "document inspector shows selected records of the current page",
                async function (assert) {
                    assert.expect(6);

                    const kanban = await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban" limit="2"><templates><t t-name="card">
                        <field name="name"/>
                </t></templates></kanban>`,
                    });

                    kanban.model.root.records[0].toggleSelection(0);
                    await nextTick();

                    assert.containsOnce(
                        target,
                        ".o_record_selected",
                        "should have 1 selected record"
                    );
                    assert.containsOnce(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        "should show 1 document preview in the DocumentsInspector"
                    );

                    await pagerNext(target);

                    assert.containsNone(
                        target,
                        ".o_record_selected",
                        "should have no selected record"
                    );
                    assert.containsNone(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        "should show no document preview in the DocumentsInspector"
                    );

                    await pagerPrevious(target);

                    assert.containsNone(
                        target,
                        ".o_record_selected",
                        "should have no selected record"
                    );
                    assert.containsNone(
                        target,
                        ".o_documents_inspector_preview .o_document_preview",
                        "should show no document preview in the DocumentsInspector"
                    );
                }
            );

            QUnit.skip("document inspector: document preview", async function (assert) {
                const views = {
                    "documents.document,false,kanban": `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                    </t></templates></kanban>`,
                };
                const { openView } = await createDocumentsViewWithMessaging({
                    serverData: { views },
                });
                await openView({
                    res_model: "documents.document",
                    views: [[false, "kanban"]],
                });

                await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                assert.containsNone(target, ".o_mimetype_icon[data-mimetype='image/png']");

                await legacyClick($(target).find(".o_kanban_record:contains(burp)")[0]);

                assert.containsNone(target, ".o-FileViewer", "should not have a document preview");
                assert.containsOnce(
                    target,
                    ".o_mimetype_icon[data-mimetype='image/png']",
                    "should have a clickable image"
                );

                await legacyClick(target, ".o_mimetype_icon[data-mimetype='image/png']");

                assert.containsOnce(target, ".o-FileViewer");
                assert.containsOnce(target, ".o-FileViewer div[aria-label='Close']");

                await legacyClick(target, ".o-FileViewer div[aria-label='Close']");

                await legacyClick($(target).find(".o_kanban_record:contains(blip)")[0]);

                await legacyClick(target, ".o_preview_available");

                assert.containsOnce(target, ".o-FileViewer div[title='Split PDF']");
                const encodedRoute = encodeURIComponent(
                    "/documents/content/2?is_document_preview=1"
                );
                assert.containsOnce(
                    target,
                    `iframe[data-src="/web/static/lib/pdfjs/web/viewer.html?file=${encodedRoute}#pagemode=none"]`,
                    "should have an iframe with the correct pdfviewer src"
                );

                await legacyClick(target, ".o-FileViewer div[aria-label='Close']");

                assert.containsNone(target, ".o-FileViewer");
            });

            QUnit.skip(
                "document inspector: open preview while modifying document",
                async function (assert) {
                    var def = testUtils.makeTestPromise();

                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                    </t></templates></kanban>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                        mockRPC: async (route, args) => {
                            if (args.method === "write") {
                                return def;
                            }
                        },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    await legacyClick($(target).find(".o_kanban_record:contains(burp)")[0]);

                    await editInput(target, "div[name=name] input", "foo");

                    await legacyClick(target, ".o_mimetype_icon[data-mimetype='image/png']");
                    await nextTick();
                    assert.containsNone(target, ".o-FileViewer");

                    def.resolve();
                    await nextTick();
                    await legacyClick(target, ".o_mimetype_icon[data-mimetype='image/png']");
                    await nextTick();
                    assert.containsOnce(target, ".o-FileViewer");
                    await legacyClick(target, ".o-FileViewer div[aria-label='Close']");
                }
            );

            QUnit.skip("document inspector: can share records", async function (assert) {
                assert.expect(3);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                    mockRPC: async (route, args) => {
                        if (args.method === "action_get_share_url") {
                            assert.deepEqual(args.args, [
                                {
                                    document_ids: [[6, false, [1, 2]]],
                                    folder_id: 1,
                                    type: "ids",
                                },
                            ]);
                            return "localhost/share";
                        }
                    },
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                await legacyClick(
                    $(target).find(".o_kanban_record:contains(yop) .o_record_selector")[0]
                );
                await legacyClick(
                    $(target).find(".o_kanban_record:contains(blip) .o_record_selector")[0]
                );

                assert.containsN(target, ".o_record_selected", 2, "should have 2 selected records");

                await legacyClick(
                    target.querySelector(".o_documents_inspector .o_inspector_share")
                );
                await nextTick();
                assert.containsN(target, ".o_notification_body", 1, "should have a notification");
            });

            QUnit.skip("document inspector: locked records", async function (assert) {
                assert.expect(6);
                const [user] = pyEnv["res.users"].search_read([["display_name", "=", "Hazard"]]);
                pyEnv.authenticate(user.login, user.password);
                patchUserWithCleanup({ userId: serverState.userId });
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                // select a record that is locked by ourself
                await legacyClick($(target).find(".o_kanban_record:contains(zip)")[0]);

                assert.hasClass(
                    target.querySelector(".o_inspector_lock"),
                    "o_locked",
                    "this attachment should be locked"
                );
                assert.notOk(
                    target.querySelector(".o_inspector_lock").disabled,
                    "lock button should not be disabled"
                );
                assert.notOk(
                    target.querySelector(".o_inspector_replace").disabled,
                    "replace button should not be disabled"
                );

                // select a record that is locked by someone else
                await legacyClick($(target).find(".o_kanban_record:contains(gnap)")[0]);

                assert.hasClass(
                    target.querySelector(".o_inspector_lock"),
                    "o_locked",
                    "this attachment should be locked as well"
                );
                assert.ok(
                    target.querySelector(".o_inspector_replace").disabled,
                    "replace button should be disabled"
                );
                assert.ok(
                    target.querySelector(".o_inspector_archive").disabled,
                    "archive button should be disabled"
                );
            });

            QUnit.skip("document inspector: can (un)lock records", async function (assert) {
                assert.expect(5);

                const [user] = pyEnv["res.users"].search_read([["display_name", "=", "Hazard"]]);
                pyEnv.authenticate(user.login, user.password);
                patchUserWithCleanup({ userId: serverState.userId });
                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                    mockRPC: async (route, args, performRpc) => {
                        if (route === "/web/dataset/call_kw/documents.document/toggle_lock") {
                            assert.deepEqual(
                                args.args,
                                [1],
                                "should call method for the correct record"
                            );
                            const record = kanban.model.root.records.find((rec) => rec.resId === 1);
                            return performRpc("", {
                                method: "write",
                                model: "documents.document",
                                args: [
                                    [1],
                                    {
                                        lock_uid: record.data.lock_uid ? false : serverState.userId,
                                    },
                                ],
                            });
                        }
                    },
                });

                await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                assert.doesNotHaveClass(
                    target.querySelector(".o_inspector_lock"),
                    "o_locked",
                    "this attachment should not be locked"
                );

                // lock the record
                await legacyClick(target.querySelector(".o_inspector_lock"));

                assert.hasClass(
                    target.querySelector(".o_inspector_lock"),
                    "o_locked",
                    "this attachment should be locked"
                );

                // unlock the record
                await legacyClick(target.querySelector(".o_inspector_lock"));

                assert.doesNotHaveClass(
                    target.querySelector(".o_inspector_lock"),
                    "o_locked",
                    "this attachment should not be locked anymore"
                );
            });

            QUnit.skip(
                "document inspector: document info with one document selected",
                async function (assert) {
                    assert.expect(6);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                </t></templates></kanban>`,
                    });

                    await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                    assert.strictEqual(
                        target.querySelector(".o_field_widget[name=name] input").value,
                        "yop",
                        "should correctly display the name"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_field_widget[name=owner_id] input").value,
                        "Hazard",
                        "should correctly display the owner"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_field_widget[name=partner_id] input").value,
                        "Lukaku",
                        "should correctly display the related partner"
                    );
                    assert.containsNone(
                        target,
                        ".o_field_many2one .o_external_button:visible",
                        "should not display the external button in many2ones"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_inspector_model_name").textContent,
                        "Task",
                        "should correctly display the resource model"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_inspector_object_name").textContent,
                        "Write specs",
                        "should correctly display the resource name"
                    );
                }
            );

            QUnit.skip(
                "document inspector: update document info with one document selected",
                async function (assert) {
                    assert.expect(7);
                    let count = 0;

                    const [deBruyneUserId] = pyEnv["res.users"].search([
                        ["display_name", "=", "De Bruyne"],
                    ]);
                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <field name="name"/>
                        <field name="owner_id"/>
                </t></templates></kanban>`,
                        mockRPC: async function (route, args) {
                            if (args.method === "write") {
                                count++;
                                switch (count) {
                                    case 1:
                                        assert.deepEqual(
                                            args.args,
                                            [[1], { owner_id: deBruyneUserId }],
                                            "should save the change directly"
                                        );
                                        break;
                                    case 2:
                                        assert.deepEqual(
                                            args.args,
                                            [[1], { owner_id: false }],
                                            "should save false value"
                                        );
                                        break;
                                }
                            }
                        },
                    });

                    const firstRecord = $(target).find(".o_kanban_record:contains(yopHazard)")[0];
                    assert.strictEqual(
                        firstRecord.textContent,
                        "yopHazard",
                        "should display the correct owner"
                    );

                    await legacyClick(firstRecord);

                    assert.hasClass(firstRecord, "o_record_selected");

                    // change m2o value
                    const input = await clickOpenM2ODropdown(target, "owner_id");
                    await editInput(input, null, "De Bruyne");
                    await clickOpenedDropdownItem(target, "owner_id", "De Bruyne");

                    assert.strictEqual(
                        firstRecord.textContent,
                        "yopDe Bruyne",
                        "should have updated the owner"
                    );
                    assert.hasClass(
                        firstRecord,
                        "o_record_selected",
                        "first record should still be selected"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_field_many2one[name=owner_id] input").value,
                        "De Bruyne",
                        "should display the new value in the many2one"
                    );

                    await editInput(input, null, "");
                }
            );

            QUnit.skip(
                "document inspector: document info with several documents selected",
                async function (assert) {
                    assert.expect(7);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t></templates></kanban>`,
                    });

                    // select two records with same m2o value
                    const blip = $(target).find(".o_kanban_record:contains(blip)")[0];
                    const gnap = $(target).find(".o_kanban_record:contains(gnap)")[0];
                    await legacyClick(blip);
                    await legacyClick(gnap, ".o_record_selector");

                    assert.hasClass(blip, "o_record_selected", "blip record should be selected");
                    assert.hasClass(gnap, "o_record_selected", "gnap record should be selected");

                    assert.strictEqual(
                        target.querySelector(".o_field_many2one[name=owner_id] span").textContent,
                        "Lukaku",
                        "should display the correct m2o value"
                    );
                    assert.containsNone(
                        target,
                        ".o_field_many2one .o_external_button:visible",
                        "should not display the external button in many2one"
                    );

                    // select a third record with another m2o value
                    const yop = $(target).find(".o_kanban_record:contains(yop)")[0];
                    await legacyClick(yop, ".o_record_selector");
                    assert.hasClass(yop, "o_record_selected", "yop record should be selected");

                    assert.strictEqual(
                        target.querySelector(".o_field_many2one[name=owner_id] span").textContent,
                        "Multiple values",
                        "should display 'Multiple values'"
                    );
                    assert.containsNone(
                        target,
                        ".o_field_many2one .o_external_button:visible",
                        "should not display the external button in many2one"
                    );
                }
            );

            QUnit.skip(
                "document inspector: update document info with several documents selected",
                async function (assert) {
                    assert.expect(10);

                    const [deBruyneUserId] = pyEnv["res.users"].search([
                        ["display_name", "=", "De Bruyne"],
                    ]);
                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                        <field name="owner_id"/>
                    </t></templates></kanban>`,
                        mockRPC: function (route, args) {
                            if (args.method === "write") {
                                assert.deepEqual(
                                    args.args,
                                    [[1, 2], { owner_id: deBruyneUserId }],
                                    "should save the change directly"
                                );
                            }
                        },
                    });

                    const firstRecord = target.querySelector(".o_kanban_record");
                    assert.strictEqual(
                        firstRecord.textContent,
                        "yopHazard",
                        "should display the correct owner (record 1)"
                    );
                    const secondRecord = target.querySelector(".o_kanban_record:nth-of-type(2)");
                    assert.strictEqual(
                        secondRecord.textContent,
                        "blipLukaku",
                        "should display the correct owner (record 2)"
                    );

                    await legacyClick(firstRecord);
                    await legacyClick(secondRecord, ".o_record_selector");

                    assert.hasClass(
                        firstRecord,
                        "o_record_selected",
                        "first record should be selected"
                    );
                    assert.hasClass(
                        secondRecord,
                        "o_record_selected",
                        "second record should be selected"
                    );

                    // change m2o value
                    const input = await clickOpenM2ODropdown(target, "owner_id");
                    await editInput(input, null, "De Bruyne");
                    await clickOpenedDropdownItem(target, "owner_id", "De Bruyne");

                    assert.strictEqual(
                        firstRecord.textContent,
                        "yopDe Bruyne",
                        "should have updated the owner of first record"
                    );
                    assert.strictEqual(
                        secondRecord.textContent,
                        "blipDe Bruyne",
                        "should have updated the owner of second record"
                    );
                    assert.hasClass(
                        firstRecord,
                        "o_record_selected",
                        "first record should still be selected"
                    );
                    assert.hasClass(
                        secondRecord,
                        "o_record_selected",
                        "second record should still be selected"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_field_many2one[name=owner_id] input").value,
                        "De Bruyne",
                        "should display the new value in the many2one"
                    );
                }
            );

            QUnit.skip(
                "document inspector: update info: handle concurrent updates",
                async function (assert) {
                    assert.expect(9);

                    const def = testUtils.makeTestPromise();
                    let nbWrite = 0;
                    let value;
                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                    </t></templates></kanban>`,
                        mockRPC: async function (route, args, performRpc) {
                            if (args.method === "write") {
                                const result = performRpc(route, args);
                                assert.step("write");
                                nbWrite++;
                                assert.deepEqual(
                                    args.args,
                                    [[1], { name: value }],
                                    "should correctly save the changes"
                                );
                                if (nbWrite === 1) {
                                    return def.then(() => result);
                                }
                                return result;
                            }
                        },
                    });

                    assert.strictEqual(
                        target.querySelector(".o_kanban_record").textContent,
                        "yop",
                        "should display the correct filename"
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));

                    // change filename value of selected record (but block RPC)
                    value = "temp name";
                    await editInput(target.querySelector("div[name=name] input"), null, value);

                    // change filename value again (this RPC isn't blocked but must wait for
                    // the first one to return)
                    value = "new name";
                    await editInput(target.querySelector("div[name=name] input"), null, value);

                    assert.step("resolve");
                    def.resolve();
                    await nextTick();

                    assert.strictEqual(
                        target.querySelector(".o_kanban_record").textContent,
                        "new name",
                        "should still display the new filename in the record"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_field_char[name=name] input").value,
                        "new name",
                        "should still display the new filename in the document inspector"
                    );

                    assert.verifySteps(["write", "resolve", "write"]);
                }
            );

            QUnit.skip("document inspector: open resource", async function (assert) {
                assert.expect(3);

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                    async mockRPC(route, args) {
                        if (args.method === "get_formview_action") {
                            assert.strictEqual(
                                args.model,
                                "res.fake",
                                "should fetch the action for res.fake"
                            );
                            assert.deepEqual(args.args[0], [1], "should get resId for res.fake");
                            return { ignore: true };
                        }
                    },
                });

                patchWithCleanup(kanban.env.services.action, {
                    doAction(action) {
                        assert.ok(action.ignore, "should call the action after loading it");
                    },
                });

                await legacyClick(target.querySelector(".o_kanban_record"));

                await legacyClick(
                    target.querySelector(".o_documents_inspector .o_inspector_object_name")
                );
            });

            QUnit.skip(
                "document inspector: display tags of selected documents",
                async function (assert) {
                    assert.expect(4);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));

                    assert.containsN(
                        target,
                        ".o_inspector_tag",
                        2,
                        "should display the tags of the selected document"
                    );

                    await legacyClick(
                        target.querySelector(".o_kanban_record:nth-of-type(2) .o_record_selector")
                    );

                    assert.containsN(
                        target,
                        ".o_record_selected",
                        2,
                        "should have 2 selected records"
                    );
                    assert.containsOnce(
                        target,
                        ".o_inspector_tag",
                        "should display the common tags between the two selected documents"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_inspector_tag").textContent.replace(/\s/g, ""),
                        "Status>Draft×",
                        "should correctly display the content of the tag"
                    );
                }
            );

            QUnit.skip(
                "document inspector: input to add tags is hidden if no tag to add",
                async function (assert) {
                    assert.expect(2);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick($(target).find(".o_kanban_record:contains(gnap)")[0]);

                    assert.containsN(target, ".o_inspector_tag", 3, "should have 3 tags");
                    assert.containsNone(
                        target,
                        ".o_inspector_tags .o_inspector_tag_add",
                        "should not have an input to add tags"
                    );
                }
            );

            QUnit.skip("document inspector: remove tag", async function (assert) {
                assert.expect(4);

                const [user] = pyEnv["res.users"].search_read([["display_name", "=", "Hazard"]]);
                pyEnv.authenticate(user.login, user.password);
                patchUserWithCleanup({ userId: serverState.userId });
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                </t></templates></kanban>`,
                    mockRPC: async function (route, args) {
                        if (args.method === "write") {
                            assert.deepEqual(
                                args.args[0],
                                [1, 5],
                                "should write on the selected records"
                            );
                            assert.deepEqual(
                                args.args[1],
                                {
                                    tag_ids: [[3, 2]],
                                },
                                "should write the correct value"
                            );
                        }
                    },
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                await legacyClick(target.querySelector(".o_kanban_record"));
                await legacyClick(
                    target.querySelector(".o_kanban_record:nth-of-type(5) .o_record_selector")
                );

                assert.containsN(target, ".o_inspector_tag", 2, "should display two tags");

                await legacyClick(
                    target.querySelector(".o_inspector_tag:nth-of-type(2) .o_inspector_tag_remove")
                );

                assert.containsOnce(target, ".o_inspector_tag", "should display one tag");
            });

            QUnit.skip("document inspector: add a tag [REQUIRE FOCUS]", async function (assert) {
                const [lastDocumentsTagId] = pyEnv["documents.tag"].search([
                    ["display_name", "=", "No stress"],
                ]);
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                                <i class="fa fa-circle mt-1 o_record_selector"/>
                                <field name="name"/>
                            </t></templates></kanban>`,
                    mockRPC: function (route, args) {
                        if (args.method === "write") {
                            assert.deepEqual(
                                args.args[0],
                                [1, 2],
                                "should write on the selected records"
                            );
                            assert.deepEqual(
                                args.args[1],
                                {
                                    tag_ids: [[4, lastDocumentsTagId]],
                                },
                                "should write the correct value"
                            );
                        }
                    },
                });

                await click(".o_search_panel_category_value:nth-of-type(2) header");
                await click(":nth-child(1 of .o_kanban_record)");
                await click(".o_kanban_record:nth-of-type(2) .o_record_selector");
                await click(".o_inspector_tags input:not(:focus)");
                await contains(".o_inspector_tags ul li", { count: 2 });
                await contains(".o_inspector_tag");
                await insertText(".o_inspector_tags input", "stress");
                await contains(".o_inspector_tags ul", { count: 0, text: "Status" });
                await click(".o_inspector_tags ul li");
                await contains(".o_inspector_tag", { count: 2 });
                await contains(".o_inspector_tags input:focus");
            });

            /**
             * Open the preview without selecting the record, and edit its values.
             */
            QUnit.skip("document inspector: edit without selecting", async function (assert) {
                assert.expect(19);

                let waitWrite = makeDeferred();

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <div>
                            <i class="fa fa-circle o_record_selector"/>
                            <field name="name"/>
                        </div>
                        <div name="document_preview">
                            <span class="open_preview">Preview</span>
                        </div>
                    </t></templates></kanban>`,
                    mockRPC: function (route, args) {
                        if (
                            ["web_save", "write"].includes(args.method) &&
                            args.model === "documents.document"
                        ) {
                            assert.step(JSON.stringify(args.args[1]));
                            waitWrite.resolve();
                        }
                    },
                });

                await click(".o_kanban_record:nth-child(4) .open_preview");

                assert.notOk(
                    target
                        .querySelector(".o_kanban_record:nth-child(4)")
                        .classList.contains("o_record_selected"),
                    "Should not select the record if we just open the preview"
                );
                assert.verifySteps([]);

                // change the partner
                await click("div[name='partner_id'] input");
                await click(".o-autocomplete--dropdown-item:nth-child(2)");
                await waitWrite;
                waitWrite = makeDeferred();
                assert.verifySteps(
                    [JSON.stringify({ partner_id: 3 })],
                    "Should have written the new partner"
                );
                assert.strictEqual(
                    target.querySelector("div[name='partner_id'] input").value,
                    "Your Company, Mitchell Admin"
                );

                // add a new tag
                await click(".o_inspector_tags input");
                await click(".o_inspector_tags .o-autocomplete--dropdown-item:nth-child(1)");
                await waitWrite;
                waitWrite = makeDeferred();
                assert.verifySteps(
                    [JSON.stringify({ tag_ids: [[4, 3]] })],
                    "Should have added the tag"
                );
                await nextTick();
                // Re-open the preview as it is closed automatically when tags are changed
                await click(".o_kanban_record:nth-child(4) .open_preview");
                await contains(".o_tag_prefix", { text: "Priority" });

                // remove the added tag
                await click(".o_inspector_tag_remove");
                await waitWrite;
                assert.verifySteps(
                    [JSON.stringify({ tag_ids: [[3, 3]] })],
                    "Should have removed the tag"
                );
                await nextTick();
                // Re-open the preview as it is closed automatically when tags are changed
                await click(".o_kanban_record:nth-child(4) .open_preview");
                await contains(".o_tag_prefix", { count: 0 });
            });

            QUnit.skip(
                "document inspector: do not suggest already linked tags",
                async function (assert) {
                    assert.expect(2);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));

                    await contains(".o_inspector_tag", { count: 2 });

                    await legacyClick(target.querySelector(".o_inspector_tags input"));
                    editInput(target.querySelector(".o_inspector_tags input"), null, "new");
                    await contains(".o_inspector_tags ul", { count: 0 });
                }
            );

            QUnit.skip(
                "document inspector: tags: trigger a search on input clicked",
                async function (assert) {
                    assert.expect(1);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                    </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));

                    legacyClick(target.querySelector(".o_inspector_tags input"));
                    await contains(".o_inspector_tags ul li");
                }
            );

            QUnit.skip("document inspector: unknown tags are hidden", async function (assert) {
                assert.expect(1);

                const [firstDocumentRecord] = pyEnv["documents.document"].search_read([]);
                pyEnv["documents.document"].write([firstDocumentRecord.id], {
                    tag_ids: [...firstDocumentRecord.tag_ids, 42],
                });
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                await legacyClick(target.querySelector(".o_kanban_record"));

                assert.containsN(
                    target,
                    ".o_inspector_tag",
                    2,
                    "should not display the unknown tag"
                );
            });

            QUnit.skip(
                "document inspector: display rules of selected documents",
                async function (assert) {
                    assert.expect(6);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));

                    assert.containsN(
                        target,
                        ".o_inspector_rule",
                        3,
                        "should display the rules of the selected document"
                    );

                    await legacyClick(
                        target.querySelector(".o_kanban_record:nth-of-type(2)"),
                        ".o_record_selector"
                    );

                    assert.containsN(
                        target,
                        ".o_record_selected",
                        2,
                        "should have 2 selected records"
                    );
                    assert.containsOnce(
                        target,
                        ".o_inspector_rule",
                        "should display the common rules between the two selected documents"
                    );
                    assert.containsOnce(
                        target,
                        ".o_inspector_rule .o_inspector_trigger_rule",
                        "should display the button for the common rule"
                    );
                    assert.strictEqual(
                        target.querySelector(".o_inspector_rule").textContent.trim(),
                        "Convincing AI not to turn evil",
                        "should correctly display the content of the rule"
                    );
                    assert.hasAttrValue(
                        target.querySelector(".o_inspector_rule button"),
                        "title",
                        "Racing for AI Supremacy",
                        "should correctly display the tooltip of the rule"
                    );
                }
            );

            QUnit.skip(
                "document inspector: displays the right amount of single record rules",
                async function (assert) {
                    assert.expect(2);

                    const [user] = pyEnv["res.users"].search_read([
                        ["display_name", "=", "Hazard"],
                    ]);
                    pyEnv.authenticate(user.login, user.password);
                    patchUserWithCleanup({ userId: serverState.userId });
                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));

                    assert.containsN(
                        target,
                        ".o_inspector_rule",
                        3,
                        "should display the rules of the selected document (2 multi record, 1 single record)"
                    );

                    await legacyClick(
                        target.querySelectorAll(".o_kanban_record")[4],
                        ".o_record_selector"
                    );

                    assert.containsN(
                        target,
                        ".o_inspector_rule",
                        2,
                        "should display the rules in common except the single record rule"
                    );
                }
            );

            QUnit.skip("document inspector: locked by another user", async function (assert) {
                assert.expect(4);

                const resUsersId1 = pyEnv["res.users"].create({});
                pyEnv["documents.document"].create({
                    folder_id: pyEnv["documents.document"].search([["type", "=", "folder"]])[0],
                    lock_uid: resUsersId1,
                    name: "lockedByAnother",
                });
                const [user] = pyEnv["res.users"].search_read([["display_name", "=", "Hazard"]]);
                pyEnv.authenticate(user.login, user.password);
                patchUserWithCleanup({ userId: serverState.userId });
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                await legacyClick($(target).find(".o_kanban_record:contains(lockedByAnother)")[0]);

                assert.containsNone(target, ".o_inspector_rule", "should not display any rule");

                assert.ok(
                    target.querySelector(".o_inspector_lock").disabled,
                    "the lock button should be disabled"
                );
                assert.ok(
                    target.querySelector(".o_inspector_replace").disabled,
                    "the replace button should be disabled"
                );
                assert.ok(
                    target.querySelector(".o_inspector_archive").disabled,
                    "the archive button should be disabled"
                );
            });

            QUnit.skip(
                "document inspector: display rules of reloaded record",
                async function (assert) {
                    assert.expect(9);

                    const kanban = await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                        <button name="some_method" type="object"/>
                    </t></templates></kanban>`,
                    });

                    patchWithCleanup(kanban.env.services.action, {
                        doActionButton(action) {
                            assert.strictEqual(
                                action.name,
                                "some_method",
                                "should call the correct method"
                            );
                            kanban.orm.write(
                                "documents.document",
                                [action.resId],
                                { name: "yop changed" },
                                kanban.context
                            );
                            action.onClose();
                        },
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                    assert.containsN(
                        target,
                        ".o_inspector_rule button",
                        3,
                        "should display the rules of the selected document"
                    );

                    assert.strictEqual(
                        target.querySelector(".o_inspector_rule:nth-of-type(1) button").textContent,
                        "Convincing AI not to turn evil",
                        "should display the right rule"
                    );

                    assert.strictEqual(
                        target.querySelector(".o_inspector_rule:nth-of-type(2) button").textContent,
                        "Follow the white rabbit",
                        "should display the right rule"
                    );

                    assert.strictEqual(
                        target.querySelector(".o_inspector_rule:nth-of-type(3) button").textContent,
                        "One record rule",
                        "should display the right rule"
                    );

                    // legacyClick on the button to reload the record
                    await legacyClick($(target).find(".o_kanban_record:contains(yop) button")[0]);

                    assert.strictEqual(
                        $(target).find(".o_record_selected:contains(yop changed)").length,
                        1,
                        "should have reloaded the updated record"
                    );

                    assert.strictEqual(
                        target.querySelector(".o_inspector_rule:nth-of-type(1) button").textContent,
                        "Convincing AI not to turn evil",
                        "should display the right rule"
                    );

                    assert.strictEqual(
                        target.querySelector(".o_inspector_rule:nth-of-type(2) button").textContent,
                        "Follow the white rabbit",
                        "should display the right rule"
                    );

                    assert.strictEqual(
                        target.querySelector(".o_inspector_rule:nth-of-type(3) button").textContent,
                        "One record rule",
                        "should display the right rule"
                    );
                }
            );

            QUnit.skip(
                "document inspector: trigger rule actions on selected documents",
                async function (assert) {
                    assert.expect(3);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t></templates></kanban>`,
                        mockRPC: async function (route, args) {
                            if (
                                args.model === "documents.workflow.rule" &&
                                args.method === "apply_actions"
                            ) {
                                assert.deepEqual(
                                    args.args[0],
                                    [1],
                                    "should execute actions on clicked rule"
                                );
                                assert.deepEqual(
                                    args.args[1],
                                    [1, 2],
                                    "should execute actions on the selected records"
                                );
                                return Promise.resolve(true);
                            }
                        },
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));
                    await legacyClick(
                        target.querySelector(".o_kanban_record:nth-of-type(2) .o_record_selector")
                    );

                    assert.containsOnce(
                        target,
                        ".o_inspector_rule",
                        "should display the common rules between the two selected documents"
                    );
                    await legacyClick(
                        target.querySelector(".o_inspector_rule .o_inspector_trigger_rule")
                    );
                }
            );

            QUnit.skip(
                "document inspector: checks the buttons deleting/editing a link between a document and a record",
                async function (assert) {
                    assert.expect(6);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                        <field name="is_editable_attachment" invisible="1"/>
                    </t></templates></kanban>`,
                        mockRPC: async function (route, args, performRPC) {
                            if (args.method === "has_access") {
                                return true;
                            } else if (
                                args.model === "documents.workflow.rule" &&
                                args.method === "unlink_record"
                            ) {
                                performRPC("", {
                                    model: "documents.document",
                                    method: "write",
                                    args: [
                                        args.args[0],
                                        {
                                            res_model: "documents.document",
                                            res_id: false,
                                            is_editable_attachment: false,
                                        },
                                    ],
                                });
                                return true;
                            }
                        },
                    });

                    // Document with an editable link.
                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );
                    await legacyClick(target.querySelector(".o_kanban_record"));

                    assert.containsOnce(
                        target,
                        ".o_inspector_model_button.o_inspector_model_edit",
                        "should display the edit button of the link between the document and the record on the inspector."
                    );
                    assert.containsOnce(
                        target,
                        ".o_inspector_model_button.o_inspector_model_delete",
                        "should display the delete button of the link between the document and the record on the inspector."
                    );

                    // Delete the link
                    await legacyClick(target.querySelector(".o_inspector_model_delete"));
                    await legacyClick(target.querySelector(".modal-footer .btn-primary"));
                    assert.containsNone(
                        target,
                        "o_inspector_custom_field .o_model_container",
                        "should display no records link to the document"
                    );

                    // Document with a non-editable link
                    await legacyClick(target.querySelector(".o_kanban_record"));
                    await legacyClick(
                        target.querySelector(".o_kanban_record:nth-of-type(2) .o_record_selector")
                    );

                    assert.containsNone(
                        target,
                        "o_inspector_custom_field .o_model_container",
                        "should display a record link to the document"
                    );
                    assert.containsNone(
                        target,
                        ".o_inspector_model_button.o_inspector_model_edit",
                        "should not display the edit button of the link between the document and the record on the inspector."
                    );
                    assert.containsNone(
                        target,
                        ".o_inspector_model_button.o_inspector_model_delete",
                        "should not display the delete button of the link between the document and the record on the inspector."
                    );
                }
            );

            QUnit.skip(
                "document inspector: quick create not enabled in dropdown",
                async function (assert) {
                    assert.expect(2);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t></templates></kanban>`,
                    });
                    await legacyClick(target.querySelector(".o_kanban_record"));
                    const input = await clickOpenM2ODropdown(target, "partner_id");
                    await editInput(input, null, "Dupont");
                    assert.strictEqual(
                        target.querySelectorAll(".ui-autocomplete .o_m2o_dropdown_option").length,
                        1,
                        "Dropdown should be opened and have only one item"
                    );
                    assert.notEqual(
                        target.querySelector(".ui-autocomplete .o_m2o_dropdown_option").textContent,
                        'Create "Dupont"',
                        "there should not be a quick create in dropdown"
                    );
                }
            );

            QUnit.skip("document inspector: edit workspace", async function (assert) {
                assert.expect(6);
                pyEnv["documents.document"].create({
                    name: "Workspace5",
                    description: "_F1-test-description_",
                    type: "folder",
                    access_internal: "view",
                });

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                    <kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t></templates></kanban>`,
                    mockRPC: async function (route, args) {
                        if (args.method === "write") {
                            assert.deepEqual(args.args, [[1, 2], { folder_id: 3 }]);
                        }
                        if (args.method === "unlink") {
                            throw new Error("Unlink should not be called !");
                        }
                    },
                });

                assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 5);
                assert.containsNone(target, ".o_record_selected");
                await legacyClick(target.querySelector(".o_record_selector"));
                await legacyClick(target.querySelectorAll(".o_record_selector")[1]);
                assert.containsN(target, ".o_record_selected", 2);
                await legacyClick(
                    target,
                    ".o_documents_inspector .o_field_widget[name=folder_id] input"
                );
                assert.containsN(
                    target,
                    ".o_documents_inspector .o_field_widget[name=folder_id] .o-autocomplete li",
                    4,
                    'All except the one without write access (i.e. the 3 from setup) + "Search More...".'
                );
                await legacyClick(
                    target.querySelectorAll(
                        ".o_documents_inspector .o_field_widget[name=folder_id] .o-autocomplete li"
                    )[2]
                );
                assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 3);
            });

            QUnit.skip(
                "document inspector: edit a required field with invalid input and click 'Ok' of alert dialog",
                async function (assert) {
                    assert.expect(8);
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                            <templates>
                                <t t-name="card" class="flex-row">
                                    <field name="name" required="True"/>
                                    <field name="folder_id" required="True"/>
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

                    // select 'yop' document having workspace 'Workspace1'
                    await legacyClick(target.querySelector(".o_kanban_record"));
                    await contains("div[name=name] input", { value: "yop" });
                    await contains("div[name=folder_id] input", { value: "Workspace1" });

                    // clear document name and click out
                    await editInput(target, "div[name=name] input", "");
                    await triggerEvent(target, "", "pointerdown");
                    await triggerEvent(target, "div[name=folder_id] input", "blur");

                    await contains(".modal-content", { text: "No valid record to save" });
                    await click(".modal-footer .btn-primary");
                    await contains("div[name=name] input", { value: "yop" });

                    // clear document workspace and click out
                    await editInput(target, "div[name=folder_id] input", "");
                    await triggerEvent(target, "", "pointerdown");
                    await triggerEvent(target, "div[name=folder_id] input", "blur");

                    await contains(".modal-content", { text: "No valid record to save" });
                    await click(".modal-footer .btn-primary");
                    await contains("div[name=folder_id] input", { value: "Workspace1" });
                }
            );

            QUnit.module("DocumentChatter");

            QUnit.skip(
                "document inspector: download button on selecting the requested document",
                async function (assert) {
                    assert.expect(2);

                    pyEnv["documents.document"].create({
                        folder_id: 1,
                        name: "request",
                        type: "binary",
                    });

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
                        <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card" class="flex-row">
                            <i class="fa fa-circle mt-1 o_record_selector"/>
                            <field name="name"/>
                        </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_kanban_record:nth-of-type(6) .o_record_selector")
                    );
                    assert.ok(
                        target.querySelector(".o_inspector_download").disabled,
                        "the download button should be disabled when a requested document is selected"
                    );

                    await legacyClick(target.querySelector(".o_kanban_record .o_record_selector"));
                    assert.ok(
                        target.querySelector(".o_inspector_download").disabled === false,
                        "the download button should be enabled when selecting requested document with another document"
                    );
                }
            );

            QUnit.skip("document chatter: open and close chatter", async function (assert) {
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
                assert.containsNone(target, ".o-mail-Chatter");

                // select a record
                await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                assert.containsNone(target, ".o-mail-Chatter");

                // open the chatter
                await click(".o_documents_inspector .o_inspector_open_chatter");
                await contains(".o-mail-Chatter");
                assert.containsOnce(target, ".o_search_panel:visible");
                assert.containsOnce(target, ".o_kanban_renderer:visible");
                assert.containsOnce(target, ".o_documents_inspector:visible");

                // close the chatter
                await click(".o-mail-Chatter-close");
                await contains(".o_document_chatter_container .o-mail-Chatter", { count: 0 });
            });

            QUnit.skip(
                "document chatter: fetch and display chatter messages",
                async function (assert) {
                    const [documentsDocumentId1] = pyEnv["documents.document"].search([]);
                    pyEnv["mail.message"].create([
                        {
                            body: "Message 2",
                            model: "documents.document",
                            res_id: documentsDocumentId1,
                        },
                        {
                            body: "Message 1",
                            model: "documents.document",
                            res_id: documentsDocumentId1,
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
                    await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);
                    await click(".o_documents_inspector .o_inspector_open_chatter");
                    await contains(".o_document_chatter_container .o-mail-Chatter");
                    await contains(
                        ".o_document_chatter_container .o-mail-Chatter .o-mail-Message",
                        { count: 2 }
                    );
                }
            );

            QUnit.skip("document chatter: fetch and display followers", async function (assert) {
                const [documentsDocumentId1] = pyEnv["documents.document"].search([]);
                const [resPartnerId1, resPartnerId2] = pyEnv["res.partner"].search([]);
                pyEnv["mail.followers"].create([
                    {
                        email: "raoul@grosbedon.fr",
                        name: "Raoul Grosbedon",
                        partner_id: resPartnerId1,
                        res_id: documentsDocumentId1,
                        res_model: "documents.document",
                    },
                    {
                        email: "raoulette@grosbedon.fr",
                        name: "Raoulette Grosbedon",
                        partner_id: resPartnerId2,
                        res_id: documentsDocumentId1,
                        res_model: "documents.document",
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

                await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);
                await click(".o_documents_inspector .o_inspector_open_chatter");
                await contains(".o_document_chatter_container .o-mail-Chatter");
                assert.containsOnce(target, ".o_document_chatter_container .o-mail-Followers");
                assert.strictEqual(
                    target.querySelector(".o-mail-Followers-counter").textContent,
                    "2"
                );
            });

            QUnit.skip("document chatter: render the activity button", async function (assert) {
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
                        assert.deepEqual(action, {
                            context: {
                                active_id: 1,
                                active_ids: [1],
                                active_model: "documents.document",
                            },
                            name: "Schedule Activity",
                            res_model: "mail.activity.schedule",
                            target: "new",
                            type: "ir.actions.act_window",
                            view_mode: "form",
                            views: [[false, "form"]],
                        });
                    },
                });

                await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                await click(".o_documents_inspector .o_inspector_open_chatter");
                await contains(".o_document_chatter_container .o-mail-Chatter");

                const $activityButtons = $(target).find(
                    ".o_document_chatter_container button:contains(Activities)"
                );
                assert.strictEqual($activityButtons.length, 1);
                await legacyClick($activityButtons[0]);
            });

            QUnit.skip("document chatter: render the activity button 2", async function (assert) {
                pyEnv["mail.activity"].create({
                    can_write: true,
                    create_uid: serverState.userId,
                    date_deadline: serializeDate(DateTime.now()),
                    display_name: "An activity",
                    res_id: pyEnv["documents.document"].search([])[0],
                    res_model: "documents.document",
                    state: "today",
                    user_id: serverState.userId,
                });

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

                await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                await click(".o_documents_inspector .o_inspector_open_chatter");
                await contains(".o_document_chatter_container .o-mail-Chatter");

                assert.containsOnce(target, ".o-mail-ActivityList");
                assert.containsOnce(target, ".o-mail-Activity", "should display an activity");
                await contains(".o-mail-Activity .btn", { text: "Mark Done" });
                await contains(".o-mail-Activity .btn", { text: "Edit" });
                await contains(".o-mail-Activity .btn", { text: "Cancel" });

                await legacyClick($(target).find(".o_kanban_record:contains(blip)")[0]);

                assert.containsOnce(target, ".o_document_chatter_container .o-mail-Chatter");
                assert.containsNone(target, ".o-mail-Activity");
            });

            QUnit.skip(
                "document chatter: can write messages in the chatter",
                async function (assert) {
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
                        async mockRPC(route, args) {
                            if (route === "/mail/get_suggested_recipients") {
                                return { 1: [] };
                            }
                            if (route === "/mail/message/post") {
                                assert.deepEqual(
                                    args.thread_id,
                                    1,
                                    "should post message on correct record"
                                );
                                assert.strictEqual(
                                    args.post_data.body,
                                    "Some message",
                                    "should post correct message"
                                );
                            }
                        },
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });
                    await click(".o_kanban_record", { text: "yop" });
                    await click(".o_inspector_open_chatter");
                    await click(".o-mail-Chatter-sendMessage");
                    await insertText(".o-mail-Composer-input", "Some message");
                    await click(".o-mail-Composer-send:enabled");
                    await contains(".o-mail-Message", { text: "Some message" });
                }
            );

            QUnit.skip(
                "document chatter: keep chatter open when switching between records",
                async function () {
                    const [documentsDocumentId1, documentsDocumentId2] = pyEnv[
                        "documents.document"
                    ].search([]);
                    pyEnv["mail.message"].create([
                        {
                            body: "Message on 'yop'",
                            model: "documents.document",
                            res_id: documentsDocumentId1,
                        },
                        {
                            body: "Message on 'blip'",
                            model: "documents.document",
                            res_id: documentsDocumentId2,
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
                    await click(".o_kanban_record", { text: "yop" });
                    await click(".o_inspector_open_chatter");
                    await contains(".o-mail-Message", { text: "Message on 'yop'" });
                    await click(".o_kanban_record", { text: "blip" });
                    await contains(".o-mail-Message", { text: "Message on 'blip'" });
                }
            );

            QUnit.skip(
                "document chatter: keep chatter open after a reload",
                async function (assert) {
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="card" class="flex-row">
                            <i class="fa fa-circle mt-1 o_record_selector"/>
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>`,
                        "documents.document,false,search": `<search>
                    <filter name="owo" string="OwO" domain="[['id', '&lt;', 4]]"/>
                </search>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                    await click(".o_documents_inspector .o_inspector_open_chatter");
                    await contains(".o_document_chatter_container .o-mail-Chatter");

                    // reload with a domain
                    await toggleSearchBarMenu(target);
                    await toggleMenuItem(target, "OwO");

                    assert.containsOnce(target, ".o_record_selected");
                    assert.containsOnce(target, ".o_document_chatter_container .o-mail-Chatter");
                }
            );

            QUnit.skip(
                "document chatter: close chatter when more than one record selected",
                async function (assert) {
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

                    await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                    await click(".o_documents_inspector .o_inspector_open_chatter");
                    await contains(".o_document_chatter_container .o-mail-Chatter");

                    await legacyClick(
                        $(target).find(".o_kanban_record:contains(blip) .o_record_selector")[0]
                    );

                    assert.containsNone(target, ".o_document_chatter_container .o-mail-Chatter");
                }
            );

            QUnit.skip(
                "document chatter: close chatter when no more selected record",
                async function (assert) {
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                <templates>
                    <t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>`,
                        "documents.document,false,search": `<search>
                <filter name="owo" string="OwO" domain="[['id', '&gt;', 4]]"/>
            </search>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    await legacyClick($(target).find(".o_kanban_record:contains(yop)")[0]);

                    await click(".o_documents_inspector .o_inspector_open_chatter");
                    await contains(".o_document_chatter_container .o-mail-Chatter", { count: 0 });

                    // reload with a domain
                    await toggleSearchBarMenu(target);
                    await toggleMenuItem(target, "OwO");

                    assert.containsNone(target, ".o_record_selected");
                    assert.containsNone(
                        document.body,
                        ".o_document_chatter_container .o-mail-Chatter"
                    );
                }
            );

            QUnit.module("DocumentsSelector");

            QUnit.skip("document selector: basic rendering", async function (assert) {
                assert.expect(19);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                assert.strictEqual(
                    target
                        .querySelectorAll(
                            ".o_search_panel .o_search_panel_section .o_search_panel_section_header"
                        )[0]
                        .textContent.trim(),
                    "Workspace",
                    "should have a 'Workspace' section"
                );
                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_category_value",
                    4,
                    "four of them should be visible"
                );
                assert.containsOnce(
                    target,
                    ".o_search_panel_label[data-tooltip='Trash']",
                    "Trash folder should be displayed"
                );
                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                assert.strictEqual(
                    target
                        .querySelector(".o_documents_inspector_preview")
                        .textContent.replace(/\s+/g, ""),
                    "_F1-test-description_",
                    "should display the first workspace"
                );

                assert.strictEqual(
                    target
                        .querySelectorAll(
                            ".o_search_panel .o_search_panel_section .o_search_panel_section_header"
                        )[1]
                        .textContent.trim(),
                    "Tags",
                    "should have a 'tags' section"
                );
                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_filter_group",
                    2,
                    "should have 2 facets"
                );

                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:nth-of-type(1) label:nth-of-type(1) > span"
                        )
                        .textContent.replace(/\s/g, ""),
                    "Priority",
                    "the first facet should be 'Priority'"
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:nth-of-type(1) label:nth-of-type(1)"
                        )
                        .title.trim(),
                    "A priority tooltip",
                    "the first facet have a tooltip"
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:last-child label:nth-of-type(1) > span"
                        )
                        .textContent.replace(/\s/g, ""),
                    "Status",
                    "the last facet should be 'Status'"
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:last-child label:nth-of-type(1)"
                        )
                        .title.trim(),
                    "A Status tooltip",
                    "the last facet should be 'Status'"
                );

                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value",
                    2,
                    "should have 2 tags in the last facet"
                );

                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:nth-of-type(1) label"
                        )
                        .textContent.trim(),
                    "Draft",
                    "the first tag in the last facet should be 'Draft'"
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:nth-of-type(1) label"
                        )
                        .title.trim(),
                    "A Status tooltip",
                    "the first tag in the last facet have a tooltip"
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:last-child label"
                        )
                        .textContent.trim(),
                    "New",
                    "the last tag in the last facet should be 'New'"
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:last-child label"
                        )
                        .title.trim(),
                    "A Status tooltip",
                    "the last tag in the last facet have a tooltip"
                );

                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_section:nth-of-type(3) .o_search_panel_section_header"
                        )
                        .textContent.trim(),
                    "Attached To",
                    "should have an 'attached to' section"
                );
                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_section:nth-of-type(3) .o_search_panel_filter_value",
                    4,
                    "should have 4 types of models"
                );
                assert.strictEqual(
                    target.querySelectorAll(".o_search_panel_filter_value")[4].innerText,
                    "Task\n2",
                    "should display the correct number of records"
                );
                assert.containsOnce(
                    target.querySelector(".o_search_panel"),
                    '.o_search_panel_section:nth-child(4) .o_search_panel_filter_value:contains("Not attached")',
                    "should at least have a no-model element"
                );
            });

            QUnit.skip("document selector: render without facets & tags", async function (assert) {
                assert.expect(2);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                    mockRPC: function (route, args) {
                        if (args.method === "search_panel_select_multi_range") {
                            return Promise.resolve({ values: [] });
                        }
                    },
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                assert.containsNone(
                    target,
                    ".o_search_panel .o_search_panel_filter_group",
                    "shouldn't have any facet"
                );
                assert.containsNone(
                    target,
                    ".o_search_panel .o_search_panel_filter_group .o_search_panel_filter_value",
                    "shouldn't have any tag"
                );
            });

            QUnit.skip("document selector: render without related models", async function (assert) {
                assert.expect(4);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                    domain: [["res_model", "=", false]],
                });

                assert.containsNone(
                    target,
                    ".o_search_panel .o_documents_selector_tags .o_search_panel_section_header",
                    "shouldn't have a 'tags' section"
                );
                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                );
                assert.strictEqual(
                    target
                        .querySelector(
                            ".o_search_panel .o_search_panel_section:nth-of-type(3) .o_search_panel_section_header"
                        )
                        .textContent.trim(),
                    "Attached To",
                    "should have an 'attached to' section"
                );
                assert.notOk(
                    [...target.querySelectorAll(".o_search_panel_filter_value")].find(
                        (el) => el.innerText.trim() === "Not attached"
                    ),
                    "should not have an unattached document"
                );
                assert.notOk(
                    [...target.querySelectorAll(".o_search_panel_filter_value")].find(
                        (el) => el.innerText.trim() === "Not a file"
                    ),
                    "should not have an unattached document"
                );
            });

            QUnit.skip("document selector: filter on related model", async function (assert) {
                assert.expect(8);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                await legacyClick(
                    target.querySelector(".o_search_panel_category_value:nth-of-type(1) header")
                );

                assert.containsN(
                    target,
                    ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                    6,
                    "should have 6 records in the renderer"
                );
                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value",
                    4,
                    "should have 4 related models"
                );

                // filter on 'Task'
                await legacyClick($(target).find(".o_search_panel_label_title:contains(Task)")[0]);
                assert.containsN(
                    target,
                    ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                    2,
                    "should have 3 records in the renderer"
                );
                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value",
                    4,
                    "should have 4 related models"
                );

                // filter on 'Attachment' (should be a disjunction)
                await legacyClick(
                    $(target).find(".o_search_panel_label_title:contains(Attachment)")[0]
                );

                assert.containsN(
                    target,
                    ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                    3,
                    "should have 3 records in the renderer"
                );
                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value",
                    4,
                    "should still have 4 related models"
                );

                // remove both filters
                await legacyClick(
                    $(target).find(".o_search_panel_label_title:contains(Attachment)")[0]
                );
                await legacyClick($(target).find(".o_search_panel_label_title:contains(Task)")[0]);

                assert.containsN(
                    target,
                    ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                    6,
                    "should have 6 records in the renderer"
                );
                assert.containsN(
                    target,
                    ".o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value",
                    4,
                    "should still have 4 related models"
                );
            });

            QUnit.skip(
                "document selector: filter on attachments without related model",
                async function (assert) {
                    assert.expect(8);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                    </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(1) header")
                    );

                    assert.containsN(
                        target,
                        ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                        6,
                        "should have 6 records in the renderer"
                    );
                    assert.containsN(
                        target,
                        ".o_search_panel .o_search_panel_filter_value",
                        4,
                        "should have 4 related models"
                    );

                    // filter on 'Not a file'
                    await legacyClick(
                        $(target).find(".o_search_panel_label_title:contains(Not a file)")[0]
                    );

                    assert.containsOnce(
                        target,
                        ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                        "should have 1 records in the renderer"
                    );
                    assert.containsN(
                        target,
                        ".o_search_panel .o_search_panel_filter_value",
                        4,
                        "should still have 4 related models"
                    );

                    // filter on 'Task'
                    await legacyClick(
                        $(target).find(".o_search_panel_label_title:contains(Task)")[0]
                    );
                    assert.containsN(
                        target,
                        ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                        3,
                        "should have 4 records in the renderer"
                    );
                    assert.containsN(
                        target,
                        ".o_search_panel .o_search_panel_filter_value",
                        4,
                        "should still have 4 related models"
                    );

                    // remove both filters
                    await legacyClick(
                        $(target).find(".o_search_panel_label_title:contains(Not a file)")[0]
                    );
                    await legacyClick(
                        $(target).find(".o_search_panel_label_title:contains(Task)")[0]
                    );

                    assert.containsN(
                        target,
                        ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                        6,
                        "should have 6 records in the renderer"
                    );
                    assert.containsN(
                        target,
                        ".o_search_panel .o_search_panel_filter_value",
                        4,
                        "should still have 4 related models"
                    );
                }
            );

            QUnit.skip(
                "document selector: mix filter on related model and search filters",
                async function (assert) {
                    assert.expect(10);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                </t></templates></kanban>`,
                        searchViewArch: `
                    <search>
                        <filter name="owo" string="OwO" domain="[['name', 'in', ['yop', 'burp', 'pom', 'wip', 'zorro']]]"/>
                    </search>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(1) header")
                    );

                    assert.containsN(
                        target,
                        ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                        6,
                        "should have 6 records in the renderer"
                    );
                    assert.strictEqual(
                        target.querySelectorAll(".o_search_panel_filter_value")[1].innerText,
                        "Task\n2",
                        "should display the correct number of records"
                    );

                    // filter on 'Task'
                    await legacyClick(
                        $(target).find(".o_search_panel_label_title:contains(Task)")[0]
                    );
                    assert.strictEqual(
                        target.querySelectorAll(
                            ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)"
                        ).length,
                        2,
                        "should have 3 records in the renderer"
                    );

                    // reload with a domain
                    await toggleSearchBarMenu(target);
                    await toggleMenuItem(target, "OwO");

                    assert.containsOnce(
                        target,
                        ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                        1,
                        "should have 1 record in the renderer"
                    );
                    assert.strictEqual(
                        target.querySelectorAll(".o_search_panel_filter_value")[1].innerText,
                        "Task\n1",
                        "should display the correct number of records"
                    );
                    assert.strictEqual(
                        target.querySelectorAll(".o_search_panel_filter_value")[0].innerText,
                        "Attachment\n1",
                        "should display the correct number of records"
                    );

                    // filter on 'Attachment'
                    await legacyClick(
                        $(target).find(".o_search_panel_label_title:contains(Attachment)")[0]
                    );

                    assert.containsN(
                        target,
                        ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)",
                        2,
                        "should have 2 records in the renderer"
                    );

                    // reload without the domain
                    await toggleSearchBarMenu(target);
                    await toggleMenuItem(target, "OwO");

                    assert.strictEqual(
                        target.querySelectorAll(
                            ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)"
                        ).length,
                        3,
                        "should have 4 record in the renderer"
                    );
                    assert.strictEqual(
                        target.querySelectorAll(".o_search_panel_filter_value")[1].innerText,
                        "Task\n2",
                        "should display the correct number of records"
                    );
                    assert.strictEqual(
                        target.querySelectorAll(".o_search_panel_filter_value")[0].innerText,
                        "Attachment\n1",
                        "should display the correct number of records"
                    );
                }
            );

            QUnit.skip(
                "document selector: selected tags are reset when switching between workspaces",
                async function (assert) {
                    assert.expect(6);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                </t></templates></kanban>`,
                        mockRPC: function (route, args) {
                            if (
                                route ===
                                    "/web/dataset/call_kw/documents.document/web_search_read" &&
                                args.model === "documents.document"
                            ) {
                                assert.step(JSON.stringify(args.kwargs.domain || []));
                            }
                        },
                    });

                    // filter on records having tag Draft
                    const input = $(target).find(
                        ".o_search_panel_filter_value:contains(Draft) input"
                    )[0];
                    await legacyClick(input);

                    assert.ok(input.checked, "tag selector should be checked");

                    // switch to Workspace2
                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(3) header")
                    );
                    assert.ok(input.checked, "tag selector should not be checked anymore");

                    assert.verifySteps([
                        '[["folder_id","child_of",1]]',
                        '["&",["folder_id","child_of",1],["tag_ids","in",[2]]]',
                        '["&",["folder_id","child_of",2],["tag_ids","in",[2]]]',
                    ]);
                }
            );

            QUnit.skip(
                "document selector: should keep its selection when adding a tag",
                async function (assert) {
                    assert.expect(5);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target.querySelector(".o_search_panel_category_value:nth-of-type(2) header")
                    );

                    // filter on records having tag Draft
                    await legacyClick(
                        $(target).find(".o_search_panel_filter_value:contains(Draft) input")[0]
                    );

                    assert.ok(
                        $(target).find(".o_search_panel_filter_value:contains(Draft) input")[0]
                            .checked,
                        "tag selector should be checked"
                    );

                    assert.strictEqual(
                        target.querySelectorAll(
                            ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)"
                        ).length,
                        4,
                        "should have records in the renderer"
                    );

                    await legacyClick(
                        target.querySelector(".o_kanban_record"),
                        ".o_record_selector"
                    );

                    const input = target.querySelector(".o_inspector_tags input");

                    editInput(input, null, "stress");
                    await contains(".o_inspector_tags ul li a");
                    await legacyClick(target, ".o_inspector_tags ul li a");
                    assert.ok(
                        $(target).find(".o_search_panel_filter_value:contains(Draft) input")[0]
                            .checked,
                        "tag selector should still be checked"
                    );
                    assert.strictEqual(
                        target.querySelectorAll(
                            ".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)"
                        ).length,
                        4,
                        "should still have the same records in the renderer"
                    );
                }
            );

            QUnit.test(
                "document selector: include archived checkbox should not be shown",
                async function (assert) {
                    assert.expect(3);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                        <field name="name"/>
                        <field name="owner_id"/>
                    </t></templates></kanban>`,
                    });

                    await toggleSearchBarMenu(target);
                    await click(".o_filter_menu .dropdown-item");
                    await contains(dsHelpers.SELECTORS.condition);
                    await contains(".form-switch label", { count: 0, text: "Include archived" });
                }
            );

            QUnit.module("SearchPanel");

            QUnit.skip(
                "SearchPanel: can drag and drop in the search panel",
                async function (assert) {
                    assert.expect(4);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
            <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
            </t></templates></kanban>`,
                        mockRPC: async function (route, args) {
                            if (args.method === "write" && args.model === "documents.document") {
                                assert.deepEqual(
                                    args.args[0],
                                    [1, 2, 4],
                                    "should write the right records"
                                );
                                assert.deepEqual(
                                    args.args[1],
                                    { folder_id: 2 },
                                    "should have written on a folder"
                                );
                                assert.step("documents.documents/write");
                            }
                        },
                    });

                    const yopRecord = $(target).find(
                        ".o_kanban_record:contains(yop) .o_record_selector"
                    )[0];
                    // selects three records
                    await legacyClick(yopRecord);
                    await legacyClick(
                        $(target).find(".o_kanban_record:contains(burp) .o_record_selector")[0]
                    );
                    await legacyClick(
                        $(target).find(".o_kanban_record:contains(blip) .o_record_selector")[0]
                    );

                    // making sure that the documentInspector is already rendered as it is painted after the selection.
                    await nextTick();

                    // starts the drag on a selected record
                    const startEvent = new Event("dragstart", { bubbles: true });
                    const dataTransfer = new DataTransfer();
                    startEvent.dataTransfer = dataTransfer;
                    yopRecord.dispatchEvent(startEvent);

                    // drop on the second search panel category (folder)
                    const endEvent = new Event("drop", { bubbles: true });
                    endEvent.dataTransfer = dataTransfer;
                    target
                        .querySelector(".o_search_panel_category_value:nth-of-type(3)")
                        .dispatchEvent(endEvent);

                    assert.verifySteps(["documents.documents/write"]);
                }
            );

            QUnit.skip(
                "SearchPanel: can not drag and hover over the search panel All selector",
                async function (assert) {
                    assert.expect(1);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
            <kanban js_class="documents_kanban"><templates draggable="true"><t t-name="card" class="flex-row">
                <i class="fa fa-circle mt-1 o_record_selector"/>
                <field name="name"/>
            </t></templates></kanban>`,
                        mockRPC: function (route, args) {
                            if (args.method === "write" && args.model === "documents.document") {
                                throw new Error(
                                    "It should not be possible to drop a record on the All selector"
                                );
                            }
                        },
                    });

                    const yopRecord = $(target).find(
                        ".o_kanban_record:contains(yop) .o_record_selector"
                    )[0];
                    const allSelector = target.querySelector(
                        ".o_search_panel_category_value:nth-of-type(1)"
                    );
                    // selects one record
                    await legacyClick(yopRecord);

                    // starts the drag on a selected record
                    const startEvent = new Event("dragstart", { bubbles: true });
                    const dataTransfer = new DataTransfer();
                    startEvent.dataTransfer = dataTransfer;
                    yopRecord.dispatchEvent(startEvent);

                    const dragenterEvent = new Event("dragenter", { bubbles: true });
                    dragenterEvent.dataTransfer = dataTransfer;
                    allSelector.dispatchEvent(dragenterEvent);
                    assert.doesNotHaveClass(
                        allSelector,
                        "o_drag_over_selector",
                        "the All selector should not have the hover effect"
                    );

                    // drop on the "All" search panel category
                    // it should not add another write step.
                    const dropEvent = new Event("drop", { bubbles: true });
                    dropEvent.dataTransfer = dataTransfer;
                    allSelector.querySelector("header").dispatchEvent(dropEvent);
                    await nextTick();
                }
            );

            QUnit.skip(
                "SearchPanel: preview is closed automatically when changing workspace/tag/facet",
                async function (assert) {
                    assert.expect(27); // 10 clicks with parent (x 2) + 7 contains (x 1)
                    pyEnv["documents.document"].create({
                        folder_id: pyEnv["documents.document"].create({
                            name: "WorkspaceYoutube",
                            type: "folder",
                            access_internal: "edit",
                        }),
                        name: "newYoutubeVideo",
                        type: "url",
                        url: "https://youtu.be/Ayab6wZ_U1A",
                    });
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban"><templates><t t-name="card">
                            <div name="document_preview" class="o_kanban_image_wrapper" t-if="record.type.raw_value == 'url'"/>
                            <field name="name"/>
                        </t></templates></kanban>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });
                    const workspaceYoutube = [
                        ".o_search_panel_label",
                        {
                            parent: [
                                ".o_search_panel_category_value",
                                { text: "WorkspaceYoutube" },
                            ],
                        },
                    ];
                    const workspace2 = [
                        ".o_search_panel_label",
                        { parent: [".o_search_panel_category_value", { text: "Workspace2" }] },
                    ];
                    const facetStatus = [
                        "input.form-check-input",
                        { parent: [".o_search_panel_group_header", { text: "Status" }] },
                    ];
                    const tagDraft = [
                        "input.form-check-input",
                        { parent: [".o_search_panel_filter_value", { text: "Draft" }] },
                    ];
                    const newYoutubeVideoDocumentPreview = [
                        ".oe_kanban_previewer",
                        { parent: [".o_kanban_record", { text: "newYoutubeVideo" }] },
                    ];
                    const openPreview = async () => {
                        await click(...workspaceYoutube);
                        await click(...newYoutubeVideoDocumentPreview);
                        await contains(".o-FileViewer");
                    };

                    // Changing workspace must close the preview
                    await openPreview();
                    await click(...workspace2);
                    await contains(".o-FileViewer", { count: 0 });
                    // Selecting a facet must close the preview
                    await openPreview();
                    await click(...facetStatus);
                    await contains(".o-FileViewer", { count: 0 });
                    await contains(".o_kanban_record", { count: 0, text: "newYoutubeVideo" });
                    await click(...facetStatus); // Unselect the facet to make the document visible again for the next test
                    // Selecting a tag must close the preview
                    await openPreview();
                    await click(...tagDraft);
                    await contains(".o-FileViewers", { count: 0 });
                }
            );

            QUnit.skip(
                "SearchPanel: should not invoke the write method when drag and drop within same workspace",
                async function (assert) {
                    assert.expect(1);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
                        <kanban js_class="documents_kanban" draggable="true">
                            <templates><t t-name="card" class="flex-row">
                                <i class="fa fa-circle mt-1 o_record_selector"/>
                                <field name="name"/>
                            </t></templates>
                        </kanban>`,
                        mockRPC: function (route, args) {
                            if (args.method === "write" && args.model === "documents.document") {
                                throw new Error(
                                    "It should not be possible to drop a record into the same/current workspace"
                                );
                            }
                        },
                    });

                    const yopRecord = $(target).find(".o_kanban_record:contains(yop)")[0];
                    const yopRecordSelector = yopRecord.querySelector(".o_record_selector");
                    // selects the record
                    await legacyClick(yopRecordSelector);
                    await nextTick();
                    assert.hasClass(yopRecord, "o_record_selected");

                    // starts the drag on a selected record
                    const startEvent = new Event("dragstart", { bubbles: true });
                    const dataTransfer = new DataTransfer();
                    startEvent.dataTransfer = dataTransfer;
                    yopRecordSelector.dispatchEvent(startEvent);

                    // drop on the same search panel category (folder)
                    // it should not add another write step.
                    const endEvent = new Event("drop", { bubbles: true });
                    endEvent.dataTransfer = dataTransfer;
                    target.querySelector("li header.active").dispatchEvent(endEvent);
                    await nextTick();
                }
            );

            QUnit.skip("SearchPanel: regular user can not edit", async function (assert) {
                assert.expect(3);

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                });
                await click(
                    ".o_search_panel_category_value:nth-of-type(2) .o_documents_search_panel_section_edit"
                );
                await nextTick();
                assert.containsOnce(target, ".o_search_panel_item_settings_popover");
                assert.containsNone(target, ".o_search_panel_value_edit_edit");
            });

            QUnit.skip("SearchPanel: can edit folders", async function (assert) {
                assert.expect(8);

                patchUserWithCleanup({
                    hasGroup: (group) => group === "documents.group_documents_manager",
                });

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                    mockRPC: async (route, args, performRpc) => {
                        if (args.method === "move_folder_to") {
                            assert.deepEqual(args.args[0], [2]);
                            assert.strictEqual(args.args[1], 1);
                            assert.notOk(args.args[2]);
                            return performRpc("", {
                                model: args.model,
                                method: "write",
                                args: [args.args[0], { parent_folder_id: args.args[1] }],
                            });
                        }
                    },
                });

                // Edition should not be enabled for "All" workspace
                assert.containsNone(
                    target,
                    ".o_search_panel_category_value:nth-of-type(1) .o_documents_search_panel_section_edit"
                );

                triggerEvent(
                    target,
                    ".o_search_panel_category_value:nth-of-type(2) .o_documents_search_panel_section_edit",
                    "click",
                    {},
                    { skipVisibilityCheck: true }
                );
                await nextTick();
                assert.containsOnce(target, ".o_search_panel_item_settings_popover");

                // Test edition of folder settings
                patchWithCleanup(kanban.env.services.action, {
                    doAction(action) {
                        assert.deepEqual(action, {
                            res_model: "documents.document",
                            res_id: 1,
                            name: "Edit",
                            type: "ir.actions.act_window",
                            target: "new",
                            views: [[false, "form"]],
                            context: {
                                create: false,
                            },
                        });
                    },
                });

                triggerEvent(
                    target,
                    ".o_search_panel_category_value:nth-of-type(2) .o_documents_search_panel_section_edit",
                    "click",
                    {},
                    { skipVisibilityCheck: true }
                );
                await nextTick();
                assert.containsOnce(target, ".o_search_panel_item_settings_popover");
                triggerEvent(target, ".o_search_panel_value_edit_edit", "click");

                // Test dragging a folder into another one
                const sourceFolder = target.querySelector(
                    ".o_search_panel_category_value:nth-of-type(3)"
                );
                const targetFolder = target.querySelector(
                    ".o_search_panel_category_value:nth-of-type(2)"
                );
                const sourceRect = sourceFolder.getBoundingClientRect();
                await dragAndDrop(sourceFolder, sourceFolder, {
                    x: sourceRect.width / 2 + 15,
                    y: sourceRect.height / 2,
                });
                await nextTick();
                assert.ok($(targetFolder).find(".o_search_panel_label_title:contains(Workspace3)"));
            });

            QUnit.skip(
                "SearchPanel: editing facet and tag opens correct view",
                async function (assert) {
                    assert.expect(4);

                    const views = {
                        "documents.facet,false,form": '<form class="facet">facet</form>',
                        "documents.tag,false,form": '<form class="tag">tag</form>',
                        "documents.facet,documents.folder_view_form,form":
                            '<form class="folder">folder</form>',
                        "documents.tag,documents.folder_view_form,form":
                            '<form class="folder">folder</form>',
                        "documents.folder,documents.folder_view_form,form":
                            '<form class="folder">folder</form>',
                    };

                    patchUserWithCleanup({
                        hasGroup: (group) => group === "documents.group_documents_manager",
                    });

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
                <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                        serverData: { views },
                    });

                    // Edition of facet opens correct view
                    triggerEvent(
                        target,
                        ".o_search_panel_filter_group:nth-of-type(1) .o_search_panel_group_header .o_documents_search_panel_section_edit",
                        "click",
                        {},
                        { skipVisibilityCheck: true }
                    );
                    await nextTick();
                    assert.containsOnce(target, ".o_search_panel_item_settings_popover");
                    triggerEvent(target, ".o_search_panel_value_edit_edit", "click", {});
                    await nextTick();
                    assert.containsOnce(target, ".o_form_view.facet");

                    triggerEvent(target, ".modal-dialog .btn-close", "click", {});

                    // Edition of tag opens correct view
                    triggerEvent(
                        target,
                        ".o_search_panel_filter_group:nth-of-type(1) .o_search_panel_filter_value .o_documents_search_panel_section_edit",
                        "click",
                        {},
                        { skipVisibilityCheck: true }
                    );
                    await nextTick();
                    assert.containsOnce(target, ".o_search_panel_item_settings_popover");
                    triggerEvent(target, ".o_search_panel_value_edit_edit", "click", {});
                    await nextTick();
                    assert.containsOnce(target, ".o_form_view.tag");
                }
            );

            QUnit.skip(
                "SearchPanel: Trash folder is displaying inactive documents",
                async function (assert) {
                    assert.expect(3);
                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
                            <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card" class="flex-row">
                                <i class="fa fa-circle mt-1 o_record_selector"/>
                                <field name="name"/>
                            </t></templates></kanban>`,
                    });
                    assert.containsN(
                        target,
                        ".o_kanban_record:not(.o_kanban_ghost)",
                        5,
                        "Should contain 5 records"
                    );
                    await click(".o_search_panel_label[data-tooltip='Trash']");
                    await nextTick();
                    assert.containsN(
                        target,
                        ".o_kanban_record:not(.o_kanban_ghost)",
                        2,
                        "Should contain 2 records"
                    );
                }
            );

            QUnit.skip("SearchPanel: updates the route", async function (assert) {
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                        <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card" class="flex-row">
                            <i class="fa fa-circle mt-1 o_record_selector"/>
                            <field name="name"/>
                        </t></templates></kanban>`,
                });

                assert.strictEqual(router.current.folder_id, 1);

                await legacyClick(target, ".o_search_panel_category_value:nth-of-type(3) header");
                assert.strictEqual(router.current.folder_id, 2);

                await legacyClick(target, ".o_search_panel_category_value:nth-of-type(1) header");
                assert.strictEqual(router.current.folder_id, false);
            });

            QUnit.module("Upload");

            QUnit.skip("documents: upload with context", async function (assert) {
                const file = new File(["hello world"], "text.txt", { type: "text/plain" });

                const mockedXHRs = [];
                this.patchDocumentXHR(mockedXHRs, (data) => {
                    assert.strictEqual(data.get("res_model"), "project");
                    assert.strictEqual(data.get("res_id"), "1");
                    assert.step("xhrSend");
                });

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
            <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card">
                <field name="name"/>
            </t></templates></kanban>`,
                    context: {
                        default_res_model: "project",
                        default_res_id: 1,
                    },
                });
                await legacyClick(target, ".o_search_panel_category_value[title='Workspace1'] header");
                await nextTick();
                await dragoverFiles(".o_kanban_renderer", [file]);
                await dropFiles(".o_documents_drop_over_zone", [file]);
                assert.verifySteps(["xhrSend"]);
            });

            QUnit.skip("documents: upload progress bars", async function (assert) {
                const file = new File(["hello world"], "text.txt", { type: "text/plain" });

                const mockedXHRs = [];
                this.patchDocumentXHR(mockedXHRs, () => assert.step("xhrSend"));

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
            <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card">
                <field name="name"/>
            </t></templates></kanban>`,
                });
                await legacyClick(target, ".o_search_panel_category_value[title='Workspace1'] header");
                await nextTick();
                await dragoverFiles(".o_kanban_renderer", [file]);
                await dropFiles(".o_documents_drop_over_zone", [file]);
                assert.verifySteps(["xhrSend"]);

                const progressEvent = new Event("progress", { bubbles: true });
                progressEvent.loaded = 250000000;
                progressEvent.total = 500000000;
                progressEvent.lengthComputable = true;
                mockedXHRs[0].upload.dispatchEvent(progressEvent);

                await nextTick();

                assert.strictEqual(
                    target.querySelector(".o_file_upload_progress_text_left").textContent,
                    "Uploading... (50%)",
                    "the current upload progress should be at 50%"
                );

                assert.containsOnce(target, ".o-file-upload-progress-bar-abort");

                progressEvent.loaded = 350000000;
                mockedXHRs[0].upload.dispatchEvent(progressEvent);

                await nextTick();

                assert.strictEqual(
                    target.querySelector(".o_file_upload_progress_text_right").textContent,
                    "(350/500MB)",
                    "the current upload progress should be at (350/500MB)"
                );
            });

            QUnit.skip("documents: max upload limit", async function (assert) {
                const file = new File(["hello world"], "text.txt", { type: "text/plain" });
                Object.defineProperty(file, "size", {
                    get: () => 67000001,
                });

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
            <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card">
                <field name="name"/>
            </t></templates></kanban>`,
                });

                patchWithCleanup(kanban.env.services.notification, {
                    add(message, _option) {
                        assert.ok(message.startsWith("Some files could not be uploaded"));
                    },
                });

                assert.strictEqual(
                    file.size,
                    67000001,
                    "Upload file size is greater than upload limit"
                );
                await legacyClick(target, ".o_search_panel_category_value[title='Workspace1'] header");
                await nextTick();
                await dragoverFiles(".o_kanban_renderer", [file]);
                await dropFiles(".o_documents_drop_over_zone", [file]);
            });

            QUnit.skip("documents: upload multiple progress bars", async function (assert) {
                const file1 = new File(["hello world"], "text1.txt", { type: "text/plain" });
                const file2 = new File(["hello world"], "text2.txt", { type: "text/plain" });
                const file3 = new File(["hello world"], "text3.txt", { type: "text/plain" });

                const mockedXHRs = [];
                this.patchDocumentXHR(mockedXHRs, () => assert.step("xhrSend"));

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
            <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card">
                <field name="name"/>
            </t></templates></kanban>`,
                });
                await legacyClick(target, ".o_search_panel_category_value[title='Workspace1'] header");
                await nextTick();

                await dragoverFiles(".o_kanban_renderer", [file1]);
                await dropFiles(".o_documents_drop_over_zone", [file1]);
                assert.verifySteps(["xhrSend"]);
                await contains(".o_kanban_record:nth-of-type(1) .o_kanban_record_title span", {
                    text: "text1.txt", // The first kanban card should be named after the file
                });
                patchWithCleanup(kanban.env.services.notification, {
                    add(message, _option) {
                        console.log({ notification_message: message });
                    },
                });
                await dragoverFiles(".o_kanban_renderer", [file2, file3]);
                await dropFiles(".o_documents_drop_over_zone", [file2, file3]);
                assert.verifySteps(["xhrSend"]);
                await contains(".o_kanban_record:nth-of-type(2) .o_kanban_record_title span", {
                    text: "2 Files", // The new kanban card should be named after the amount of files
                });
                assert.containsN(target, ".o_kanban_progress_card", 2, "There should be 2 cards");

                // simulates 1st upload successful completion
                mockedXHRs[1].response = JSON.stringify({
                    success: "All files uploaded",
                });
                mockedXHRs[1].dispatchEvent(new Event("load"));

                // awaiting next tick as the render of the notify card isn't synchronous
                await nextTick();

                assert.containsOnce(
                    target,
                    ".o_kanban_progress_card",
                    "There should only be one card left"
                );
            });

            QUnit.skip("documents: notifies server side errors", async function (assert) {
                const file = new File(["hello world"], "text.txt", { type: "text/plain" });

                const mockedXHRs = [];
                this.patchDocumentXHR(mockedXHRs);

                const kanban = await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
            <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card">
                <field name="name"/>
            </t></templates></kanban>`,
                });

                patchWithCleanup(kanban.env.services.notification, {
                    add(message, _option) {
                        assert.strictEqual(
                            message,
                            "One or more file(s) failed to upload",
                            "the notification message should be the response error message"
                        );
                    },
                });

                await dragoverFiles(".o_kanban_renderer", [file]);
                await dropFiles(".o_documents_drop_over_zone", [file]);
                // simulates 1st upload server side error completion
                mockedXHRs[0].response = JSON.stringify({
                    error: "One or more file(s) failed to upload",
                });
                mockedXHRs[0].status = 200;
                mockedXHRs[0].dispatchEvent(new Event("load"));
                await nextTick();

                assert.containsNone(
                    target,
                    ".o_kanban_progress_card",
                    "There should be no upload card left"
                );
            });

            QUnit.skip("documents Kanban: displays youtube thumbnails", async function (assert) {
                assert.expect(1);

                pyEnv["documents.document"].create({
                    folder_id: pyEnv["documents.folder"].search([])[0],
                    name: "youtubeVideo",
                    type: "url",
                    url: "https://youtu.be/Ayab6wZ_U1A",
                });

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                    <i class="fa fa-circle mt-1 o_record_selector"/>
                    <field name="name"/>
                </t></templates></kanban>`,
                });

                await legacyClick(
                    $(target).find(".o_kanban_record:contains(youtubeVideo) .o_record_selector")[0]
                );

                assert.strictEqual(
                    target.querySelector(
                        ".o_documents_inspector img, .o_documents_single_preview .o_preview_available"
                    ).dataset.src,
                    "https://img.youtube.com/vi/Ayab6wZ_U1A/0.jpg",
                    "the inspector should display the thumbnail of the youtube video"
                );
            });

            QUnit.skip("documents List: multi selection", async function (assert) {
                assert.expect(4);

                await createDocumentsView({
                    type: "list",
                    resModel: "documents.document",
                    arch: `
                <list js_class="documents_list">
                    <field name="type" invisible="1"/>
                    <field name="name"/>
                    <field name="partner_id"/>
                    <field name="owner_id"/>
                    <field name="type"/>
                </list>`,
                });

                await legacyClick(target.querySelector(".o_data_row:nth-of-type(2)"));
                assert.ok(
                    target.querySelector(".o_data_row:nth-of-type(2) input").checked,
                    "the record should be selected"
                );

                triggerEvent(target.querySelector(".o_data_row:nth-of-type(5)"), null, "click", {
                    shiftKey: true,
                });
                await nextTick();
                assert.containsN(
                    target,
                    ".o_list_record_selector input:checked",
                    4,
                    "there should be 4 selected records"
                );

                await legacyClick(target.querySelector("thead .o_list_record_selector input"));
                assert.containsN(
                    target,
                    ".o_list_record_selector input:checked",
                    6,
                    "All (6) records should be selected"
                );

                await legacyClick(target.querySelector("thead .o_list_record_selector input"));
                assert.containsNone(
                    target,
                    ".o_list_record_selector input:checked",
                    "No record should be selected"
                );
            });

            QUnit.skip("documents List: selection using keyboard", async function (assert) {
                assert.expect(6);

                await createDocumentsView({
                    type: "list",
                    resModel: "documents.document",
                    arch: `
            <list js_class="documents_list">
                <field name="type" invisible="1"/>
                <field name="name"/>
                <field name="partner_id"/>
                <field name="owner_id"/>
                <field name="type"/>
            </list>`,
                });

                let recordSelector = target.querySelector(
                    ".o_data_row:nth-of-type(5) .o_list_record_selector"
                );
                recordSelector.focus();
                triggerEvent(recordSelector, null, "keydown", {
                    key: "Enter",
                });
                await nextTick();
                assert.containsOnce(
                    target,
                    ".o_list_record_selector input:checked",
                    "there should be 1 selected record"
                );
                assert.ok(
                    recordSelector.querySelector("input").checked,
                    "the right record should be selected"
                );

                recordSelector = target.querySelector(
                    ".o_data_row:nth-of-type(4) .o_list_record_selector"
                );
                recordSelector.focus();
                triggerEvent(recordSelector, null, "keydown", {
                    key: "Enter",
                });
                await nextTick();
                assert.containsOnce(
                    target,
                    ".o_list_record_selector input:checked",
                    "there should be 1 selected record"
                );
                assert.ok(
                    recordSelector.querySelector("input").checked,
                    "the right record should be selected"
                );

                // Press Enter key with Shift key should select multiple records
                recordSelector = target.querySelector(
                    ".o_data_row:nth-of-type(3) .o_list_record_selector"
                );
                recordSelector.focus();
                triggerEvent(recordSelector, null, "keydown", {
                    key: "Enter",
                    shiftKey: true,
                });
                await nextTick();
                assert.containsN(
                    target,
                    ".o_list_record_selector input:checked",
                    2,
                    "there should be 2 selected records"
                );

                recordSelector = target.querySelector(
                    ".o_data_row:nth-of-type(2) .o_list_record_selector"
                );
                recordSelector.focus();
                triggerEvent(recordSelector, null, "keydown", {
                    key: " ",
                });
                await nextTick();
                assert.containsN(
                    target,
                    ".o_list_record_selector input:checked",
                    3,
                    "there should be 3 selected records"
                );
            });

            QUnit.skip("documents: Versioning", async function (assert) {
                assert.expect(13);

                const irAttachmentId1 = pyEnv["ir.attachment"].create({
                    name: "oldYoutubeVideo",
                    create_date: "2019-12-09 14:13:21",
                    create_uid: serverState.userId,
                });
                const documentsDocumentId1 = pyEnv["documents.document"].create({
                    folder_id: pyEnv["documents.folder"].search([])[0],
                    name: "newYoutubeVideo",
                    type: "url",
                    url: "https://youtu.be/Ayab6wZ_U1A",
                    previous_attachment_ids: [irAttachmentId1],
                });

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                <kanban js_class="documents_kanban" draggable="true"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
                    async mockRPC(route, args) {
                        if (args.model === "ir.attachment" && args.method === "unlink") {
                            assert.deepEqual(
                                args.args[0],
                                [irAttachmentId1],
                                "should unlink the right attachment"
                            );
                            assert.step("attachmentUnlinked");
                            return true;
                        }
                        if (args.model === "documents.document" && args.method === "write") {
                            assert.deepEqual(
                                args.args[0],
                                [documentsDocumentId1],
                                "should target the right document"
                            );
                            assert.deepEqual(
                                args.args[1],
                                { attachment_id: irAttachmentId1 },
                                "should target the right attachment"
                            );
                            assert.step("attachmentRestored");
                            return true;
                        }
                    },
                });

                await legacyClick(target.querySelector(".o_kanban_record:nth-of-type(6)"));

                assert.strictEqual(
                    target.querySelector(".o_inspector_history_name").textContent,
                    "oldYoutubeVideo",
                    "should display the correct record name"
                );
                assert.strictEqual(
                    target.querySelector(".o_inspector_history_create_name").textContent,
                    "Your Company, Mitchell Admin",
                    "should display the correct name"
                );
                assert.strictEqual(
                    target.querySelector(".o_inspector_history_info_date").textContent,
                    "12/9/2019",
                    "should display the correct date"
                );

                assert.containsOnce(
                    target,
                    ".o_inspector_history_item_restore",
                    "There should be one restore button"
                );
                assert.containsOnce(
                    target,
                    ".o_inspector_history_item_download",
                    "There should be one download button"
                );
                assert.containsOnce(
                    target,
                    ".o_inspector_history_item_delete",
                    "There should be one delete button"
                );

                await legacyClick(target.querySelector(".o_inspector_history_item_restore"));
                assert.verifySteps(["attachmentRestored"]);
                await legacyClick(target.querySelector(".o_inspector_history_item_delete"));
                assert.verifySteps(["attachmentUnlinked"]);
            });

            QUnit.skip("store and retrieve active category value", async function (assert) {
                assert.expect(9);

                let expectedActiveId = 3;
                const storageKey = "searchpanel_documents_document";
                const ramStorage = makeRAMLocalStorage();
                const getItem = ramStorage.getItem.bind(ramStorage);
                const setItem = ramStorage.setItem.bind(ramStorage);
                const storage = Object.assign(ramStorage, {
                    getItem(key) {
                        const value = getItem(key);
                        if (key === storageKey) {
                            assert.step(`storage get ${value}`);
                        }
                        return value;
                    },
                    setItem(key, value) {
                        if (key === storageKey) {
                            assert.step(`storage set ${value}`);
                        }
                        setItem(key, value);
                    },
                });
                storage.setItem(storageKey, expectedActiveId);
                patchWithCleanup(browser, {
                    localStorage: storage,
                });
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                <kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="card">
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>`,
                    async mockRPC(route, args) {
                        if (
                            route === "/web/dataset/call_kw/documents.document/web_search_read" &&
                            args.model === "documents.document"
                        ) {
                            assert.deepEqual(args.kwargs.domain, [
                                ["folder_id", "child_of", expectedActiveId],
                            ]);
                        }
                    },
                });

                assert.containsOnce(target, ".o_search_panel_category_value .active");
                assert.containsOnce(
                    target,
                    ".o_search_panel_category_value:nth-of-type(1) .active"
                );

                expectedActiveId = 2;
                await legacyClick(target, ".o_search_panel_category_value:nth-of-type(3) header");

                assert.verifySteps([
                    "storage set 3", // Manual set for initial value
                    "storage get 3",
                    "storage set 3",
                    "storage set 2", // Set on toggle
                ]);
            });

            QUnit.skip("retrieved category value does not exist", async function (assert) {
                assert.expect(5);

                const storageKey = "searchpanel_documents_document";
                const ramStorage = makeRAMLocalStorage();
                const getItem = ramStorage.getItem.bind(ramStorage);
                const storage = Object.assign(ramStorage, {
                    getItem(key) {
                        const value = getItem(key);
                        if (key === storageKey) {
                            assert.step(`storage get ${value}`);
                        }
                        return value;
                    },
                });
                storage.setItem(storageKey, 343);
                patchWithCleanup(browser, {
                    localStorage: storage,
                });
                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `
                <kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="card">
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>`,
                    async mockRPC(route, args) {
                        if (
                            route === "/web/dataset/call_kw/documents.document/web_search_read" &&
                            args.model === "documents.document"
                        ) {
                            assert.deepEqual(args.kwargs.domain, [["folder_id", "child_of", 1]]);
                        }
                    },
                });

                assert.containsOnce(target, ".o_search_panel_category_value .active");
                assert.containsOnce(target, ".o_search_panel_category_value:nth(1) .active");

                assert.verifySteps(["storage get 343"]);
            });

            QUnit.skip(
                "documents kanban: unselect all by clicking outside of the records",
                async function (assert) {
                    assert.expect(2);

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                        <i class="fa fa-circle mt-1 o_record_selector"/>
                        <field name="name"/>
                    </t></templates></kanban>`,
                    });

                    const firstRecord = target.querySelector(".o_kanban_record");
                    await triggerEvent(firstRecord, null, "keydown", {
                        key: "Enter",
                    });
                    const secondRecord = target.querySelectorAll(".o_kanban_record")[1];
                    await triggerEvent(secondRecord, null, "keydown", {
                        key: "Enter",
                        shiftKey: true,
                    });
                    assert.containsN(target, ".o_record_selected", 2);
                    await legacyClick(target, ".o_kanban_renderer");
                    assert.containsN(target, ".o_record_selected", 0);
                }
            );

            QUnit.skip(
                "documents list: unselect all by clicking outside of the records",
                async function (assert) {
                    assert.expect(2);

                    await createDocumentsView({
                        type: "list",
                        resModel: "documents.document",
                        arch: `
            <list js_class="documents_list">
                <field name="type" invisible="1"/>
                <field name="name"/>
                <field name="partner_id"/>
                <field name="owner_id"/>
                <field name="type"/>
            </list>`,
                    });

                    const firstRecord = target.querySelector(".o_data_row");
                    await triggerEvent(firstRecord, null, "keydown", {
                        key: "Enter",
                    });
                    const secondRecord = target.querySelectorAll(".o_data_row")[1];
                    await triggerEvent(secondRecord, null, "keydown", {
                        key: "Enter",
                        shiftKey: true,
                    });
                    assert.containsN(target, ".o_data_row_selected", 2);
                    await legacyClick(target, ".o_list_renderer");
                    assert.containsN(target, ".o_data_row_selected", 0);
                }
            );

            QUnit.test(
                "documents list: don't unselect all when interacting with the headers",
                async function (assert) {
                    assert.expect(2);

                    await createDocumentsView({
                        type: "list",
                        resModel: "documents.document",
                        arch: `
                            <list js_class="documents_list">
                                <field name="type" invisible="1"/>
                                <field name="name"/>
                                <field name="partner_id"/>
                                <field name="owner_id"/>
                                <field name="type"/>
                            </list>`,
                    });

                    const firstRecord = target.querySelector(".o_data_row");
                    await legacyClick(firstRecord, ".o_list_record_selector input");
                    const secondRecord = target.querySelectorAll(".o_data_row")[1];
                    await legacyClick(secondRecord, ".o_list_record_selector input");
                    assert.containsN(target, ".o_data_row_selected", 2);

                    const th2 = target.querySelector("th:nth-child(2)");
                    const resizeHandle = th2.querySelector(".o_resize");

                    // This should be `await dragAndDrop(resizeHandle, target.querySelector("th:nth-child(3)"))`
                    // But the dragAndDrop doesn't trigger a click event like it is supposed to
                    await legacyClick(resizeHandle);
                    assert.containsN(target, ".o_data_row_selected", 2);
                }
            );

            QUnit.skip(
                "documents Kanban: workspace user will be able to share document",
                async function (assert) {
                    assert.expect(2);
                    pyEnv["documents.folder"].create({
                        name: "Workspace5",
                        description: "_F1-test-description_",
                        has_write_access: false,
                    });

                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
                        <kanban js_class="documents_kanban"><templates><t t-name="card" class="flex-row">
                            <i class="fa fa-circle mt-1 o_record_selector"/>
                            <field name="name"/>
                        </t></templates></kanban>`,
                    });

                    await legacyClick(
                        target,
                        ".o_search_panel_category_value:nth-of-type(4) header"
                    );
                    await nextTick();
                    assert.strictEqual(
                        target
                            .querySelector(".o_search_panel_category_value > header.active")
                            .textContent.trim(),
                        "Workspace5",
                        'should have a "Workspace5" selected'
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_share_domain").disabled,
                        "the share button should be enabled when a folder is selected"
                    );
                }
            );

            QUnit.skip(
                "documents previewer : download button on documents without attachment",
                async function (assert) {
                    assert.expect(4);
                    pyEnv["documents.document"].create({
                        folder_id: pyEnv["documents.folder"].search([])[0],
                        name: "newYoutubeVideo",
                        type: "url",
                        url: "https://youtu.be/Ayab6wZ_U1A",
                    });
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban"><templates><t t-name="card">
                            <div name="document_preview" class="o_kanban_image_wrapper" t-if="record.type.raw_value == 'url'">
                                <img width="100" height="100" class="o_attachment_image"/>
                            </div>
                            <field name="name"/>
                        </t></templates></kanban>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    [...target.querySelectorAll(".oe_kanban_previewer")].pop().click();
                    await nextTick();

                    assert.containsOnce(target, ".o-FileViewer", "should have a document preview");
                    assert.containsOnce(
                        target,
                        "[title='Close (Esc)']",
                        "should have a close button"
                    );
                    assert.containsNone(
                        target,
                        ".o-FileViewer-download",
                        "should not have a download button"
                    );
                    target.querySelector("[title='Close (Esc)']").click();
                    await nextTick();
                    assert.containsNone(
                        target,
                        ".o-FileViewer",
                        "should not have a document preview"
                    );
                }
            );

            QUnit.skip(
                "documents list : uploding the requested documents with multiple selection",
                async function (assert) {
                    pyEnv["documents.document"].unlink(pyEnv["documents.document"].search([]));
                    const documentIds = pyEnv["documents.document"].create([
                        {
                            folder_id: 1,
                            name: "request",
                            type: "binary",
                        },
                        {
                            folder_id: 1,
                            name: "request1",
                            type: "binary",
                        },
                        {
                            folder_id: 1,
                            name: "request2",
                            type: "binary",
                        },
                    ]);
                    const text = new File(["hello world"], "text.txt", { type: "text/plain" });
                    this.patchDocumentXHR([], (data) => {
                        const datas = Object.fromEntries(data.entries());
                        assert.strictEqual(
                            Number(datas.document_id),
                            documentIds[1],
                            "The selected requsted document should be uploaded"
                        );
                        assert.strictEqual(datas.ufile.name, "text.txt");
                        assert.step("xhrSend");
                    });
                    await createDocumentsView({
                        type: "list",
                        resModel: "documents.document",
                        arch: `<list js_class="documents_list">
                            <field name="name"/>
                        </list>`,
                    });
                    // select 3 requested documents
                    await legacyClick(target, ".o_list_record_selector.o_list_controller");
                    const fileInput = target.querySelector(".o_inspector_replace_input");
                    // legacyClick on the 2nd document to upload
                    fileInput.setAttribute("data-index", 1);
                    await inputFiles(".o_inspector_replace_input", [text]);
                    assert.verifySteps(["xhrSend"]);
                }
            );

            QUnit.skip(
                "when no sharable workspace is present, check the visibility of control panel buttons inside 'All' workspace",
                async function (assert) {
                    pyEnv["documents.folder"].unlink(pyEnv["documents.folder"].search([]));
                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `<kanban js_class="documents_kanban">
                                    <templates>
                                        <t t-name="card" class="flex-row">
                                            <i class="fa fa-circle mt-1 o_record_selector"/>
                                            <field name="name"/>
                                        </t>
                                    </templates>
                                </kanban>`,
                    });
                    await click(".o_search_panel_category_value:nth-of-type(1) header");
                    await nextTick();
                    assert.ok(
                        target.querySelector(".o_documents_kanban_upload").disabled,
                        "the upload button should be disabled"
                    );
                    assert.ok(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the link button should be disabled"
                    );
                    assert.ok(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be disabled"
                    );
                    assert.ok(
                        target.querySelector(".o_documents_kanban_spreadsheet").disabled,
                        "the spreadsheet button should be disabled"
                    );
                    assert.ok(
                        target.querySelector(".o_documents_kanban_share_domain").disabled,
                        "the share button should be disabled"
                    );
                }
            );

            QUnit.skip(
                "click events triggered inside the FileViewer should not bubble up to trigger the event bound on the DocumentsKanbanRenderer",
                async function (assert) {
                    assert.expect(6);

                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: {
                            views: {
                                "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                                    <templates>
                                        <t t-name="card">
                                            <field name="name"/>
                                        </t>
                                    </templates>
                                </kanban>`,
                            },
                        },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });
                    patchWithCleanup(DocumentsKanbanRenderer.prototype, {
                        onGlobalClick(ev) {
                            super.onGlobalClick(ev);
                            assert.step("global click");
                        },
                    });
                    await legacyClick($(target).find(".o_kanban_record:contains(burp)")[0]);
                    assert.containsOnce(
                        target,
                        ".o_mimetype_icon[data-mimetype='image/png']",
                        "should have a clickable image"
                    );
                    await legacyClick(target, ".o_mimetype_icon[data-mimetype='image/png']");
                    assert.containsOnce(target, ".o-FileViewer");

                    assert.containsOnce(target, ".o-FileViewer-header");
                    await legacyClick(target, ".o-FileViewer-header");

                    assert.containsOnce(
                        target,
                        ".o-FileViewer-navigation[title='Next (Right-Arrow)']"
                    );
                    await legacyClick(
                        target,
                        ".o-FileViewer-navigation[title='Next (Right-Arrow)']"
                    );
                    await legacyClick(target, ".o-FileViewer-headerButton[title='Close (Esc)']");

                    // to verify the patchWithCleanup above works
                    await legacyClick(target.querySelectorAll(".o_kanban_ghost")[2]);
                    assert.verifySteps(["global click"]);
                }
            );

            QUnit.skip(
                "documents Kanban : preview automatically close while restoring a document",
                async function (assert) {
                    await createDocumentsView({
                        type: "kanban",
                        resModel: "documents.document",
                        arch: `
                            <kanban js_class="documents_kanban"><templates><t t-name="card">
                                <div name="document_preview">
                                    <field name="name"/>
                                </div>
                            </t></templates></kanban>`,
                    });
                    await legacyClick(target, ".o_search_panel_label[data-tooltip='Trash']");
                    await legacyClick(
                        target,
                        ".o_kanban_record:nth-of-type(2) [name='document_preview']"
                    );
                    assert.containsOnce(target, ".o-FileViewer-view");
                    await legacyClick(target, ".o_archived");
                    assert.containsNone(target, ".o-FileViewer-view");
                }
            );

            QUnit.skip("SearchPanel: can share workspace", async function (assert) {
                assert.expect(8);

                patchWithCleanup(navigator.clipboard, {
                    async writeText(text) {
                        assert.step("copy");
                    },
                });

                await createDocumentsView({
                    type: "kanban",
                    resModel: "documents.document",
                    arch: `<kanban js_class="documents_kanban"><templates><t t-name="card">
                                <field name="name"/>
                            </t></templates></kanban>`,
                    mockRPC: async function (route, args) {
                        if (args.method === "web_save") {
                            assert.deepEqual(args.kwargs.context, {
                                default_domain: [["folder_id", "child_of", 1]],
                                default_folder_id: 1,
                                default_type: "domain",
                                lang: "en",
                                tz: "taht",
                                uid: 2,
                            });
                            assert.step("web_save");
                        }
                    },
                });
                assert.containsNone(
                    target,
                    ".o_search_panel_category_value:nth-of-type(1) .o_documents_search_panel_section_edit"
                );
                await click(
                    ".o_search_panel_category_value:nth-of-type(2) .o_documents_search_panel_section_edit"
                );
                await nextTick();
                assert.containsOnce(target, ".o_search_panel_item_settings_popover");
                await legacyClick(target, ".o_search_panel_value_share");
                assert.verifySteps([]);
                await legacyClick($(".o_form_button_save").get(0));
                assert.verifySteps(["web_save", "copy"]);
            });
        }
    );
});
