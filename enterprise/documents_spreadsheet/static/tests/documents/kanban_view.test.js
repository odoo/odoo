import { DocumentsSearchPanel } from "@documents/views/search/documents_search_panel";
import { basicDocumentsKanbanArch } from "@documents/../tests/helpers/views/kanban";
import { getDocumentsTestServerData } from "@documents/../tests/helpers/data";
import {
    defineDocumentSpreadsheetModels,
    getMySpreadsheetPermissionPanelData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { makeDocumentsSpreadsheetMockEnv } from "@documents_spreadsheet/../tests/helpers/model";
import { mockActionService } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Model } from "@odoo/o-spreadsheet";
import {
    contains,
    mountView,
    onRpc,
    patchWithCleanup,
    preloadBundle,
    serverState,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { download } from "@web/core/network/download";
import { deepEqual } from "@web/core/utils/objects";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { getEnrichedSearchArch } from "@documents/../tests/helpers/views/search";

describe.current.tags("desktop");
defineDocumentSpreadsheetModels();
preloadBundle("spreadsheet.o_spreadsheet");

let target;

const basicDocumentKanbanArch = basicDocumentsKanbanArch.replace(
    `<field name="name"/>`,
    `<field name="name"/><field name="handler"/>`
);

/**
 * @returns {Object}
 */
function getTestServerData(spreadsheetData = {}) {
    return getDocumentsTestServerData([
        {
            id: 2,
            name: "My spreadsheet",
            display_name: "My spreadsheet",
            spreadsheet_data: JSON.stringify(spreadsheetData),
            is_favorited: false,
            folder_id: 1,
            handler: "spreadsheet",
            access_token: "accessTokenMyspreadsheet",
            owner_id: serverState.userId,
        },
    ]);
}

beforeEach(() => {
    target = getFixture();
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
});

test("download frozen spreadsheet", async function () {
    const serverData = getTestServerData();
    // Only frozen spreadsheet can be downloaded in document.
    serverData.models["ir.attachment"] = { records: [{ id: 1 }] };
    serverData.models["documents.document"].records[1].handler = "frozen_spreadsheet";
    serverData.models["documents.document"].records[1].attachment_id = 1;
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
    });
    patchWithCleanup(download, {
        _download: async (options) => {
            expect.step(options.url);
            expect(deepEqual(options.data, {})).toBe(true);
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_kanban_record:contains(My spreadsheet) .o_record_selector").click({
        ctrlKey: true,
    });
    await contains("button:contains(Download)").click();
    await animationFrame();
    expect.verifySteps(["/documents/content/accessTokenMyspreadsheet"]);
});

test("share a spreadsheet", async function () {
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    const spreadsheetId = 2;
    const serverData = getTestServerData();
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("Document url copied");
            expect(url).toBe("https://localhost:8069/odoo/documents/accessTokenMyspreadsheet");
        },
    });
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(spreadsheetId);
                expect.step("permission_panel_data");
                return getMySpreadsheetPermissionPanelData();
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    expect(target.querySelector(".spreadsheet_share_dropdown")).toBe(null);
    await contains(".o_kanban_record:contains(My spreadsheet) .o_record_selector").click({
        ctrlKey: true,
    });
    await contains("button:contains(Share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "Document url copied"]);
});

test("Freeze&Share a spreadsheet", async function () {
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    const spreadsheetId = 2;
    const frozenSpreadsheetId = 1337;
    const model = new Model();
    const serverData = getTestServerData();
    serverData.models["documents.document"].records[1].spreadsheet_data = JSON.stringify(
        model.exportData()
    );
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("Document url copied");
            expect(url).toBe("https://localhost:8069/odoo/documents/accessTokenMyspreadsheet");
        },
    });
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "action_freeze_and_copy") {
                const excel = JSON.parse(JSON.stringify(model.exportXLSX().files));

                expect(args.args[0]).toEqual(spreadsheetId);
                expect(args.args[1]).toEqual(JSON.stringify(model.exportData()));
                expect(args.args[2]).toEqual(excel);

                expect.step("spreadsheet_shared");
                return { id: frozenSpreadsheetId };
            }
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(frozenSpreadsheetId);
                expect.step("permission_panel_data");
                return getMySpreadsheetPermissionPanelData();
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    expect(target.querySelector(".spreadsheet_share_dropdown")).toBe(null);
    await contains(".o_kanban_record:contains(My spreadsheet) .o_record_selector").click({
        ctrlKey: true,
    });
    await contains("button:contains(Freeze and share)").click();
    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["spreadsheet_shared", "permission_panel_data", "Document url copied"]);
});

test("open xlsx converts to o-spreadsheet, clone it and opens the spreadsheet", async function () {
    const spreadsheetId = 10;
    const spreadsheetCopyId = 99;
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = { records: [{ id: 1 }] };
    serverData.models["documents.document"].records.push({
        id: spreadsheetId,
        name: "My excel file",
        mimetype: XLSX_MIME_TYPES[0],
        thumbnail_status: "present",
        type: "binary",
        attachment_id: 1, // Necessary to not be considered as a request
    });
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async (route, args) => {
            if (args.method === "clone_xlsx_into_spreadsheet") {
                expect.step("spreadsheet_cloned");
                expect(args.model).toBe("documents.document");
                expect(args.args).toEqual([spreadsheetId]);
                return spreadsheetCopyId;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    mockActionService((action) => {
        expect.step(action.tag);
        expect(action.params.spreadsheet_id).toEqual(spreadsheetCopyId);
    });
    await contains(".o_kanban_record:contains('My excel file') .o_kanban_image_wrapper").click();

    // confirm conversion to o-spreadsheet
    await contains(".modal-content .btn.btn-primary").click();
    expect.verifySteps(["spreadsheet_cloned", "action_open_spreadsheet"]);
});

test("open WPS-marked xlsx converts to o-spreadsheet, clone it and opens the spreadsheet", async function () {
    const spreadsheetId = 10;
    const spreadsheetCopyId = 99;
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = { records: [{ id: 1 }] };
    serverData.models["documents.document"].records.push({
        id: spreadsheetId,
        folder_id: 1,
        name: "My excel file",
        mimetype: XLSX_MIME_TYPES[1],
        thumbnail_status: "present",
        type: "binary",
        attachment_id: 1, // Necessary to not be considered as a request
    });
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async (route, args) => {
            if (args.method === "clone_xlsx_into_spreadsheet") {
                expect.step("spreadsheet_cloned");
                expect(args.model).toBe("documents.document");
                expect(args.args).toEqual([spreadsheetId]);
                return spreadsheetCopyId;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    mockActionService((action) => {
        expect.step(action.tag);
        expect(action.params.spreadsheet_id).toEqual(spreadsheetCopyId);
    });
    await contains(".o_kanban_record:contains('My excel file') .oe_kanban_previewer").click();

    // confirm conversion to o-spreadsheet
    await contains(".modal-content .btn.btn-primary").click();
    expect.verifySteps(["spreadsheet_cloned", "action_open_spreadsheet"]);
});

test("download a frozen spreadsheet document while selecting requested document", async function () {
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    onRpc("/documents/touch/accessTokenRequest", () => true);
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = { records: [{ id: 1 }] };
    serverData.models["documents.document"].records = [
        {
            name: "My spreadsheet",
            raw: "{}",
            is_favorited: false,
            folder_id: false,
            handler: "frozen_spreadsheet",
            type: "binary",
            access_token: "accessTokenMyspreadsheet",
            attachment_id: 1, // Necessary to not be considered as a request
        },
        {
            name: "Request",
            folder_id: false,
            type: "binary",
            access_token: "accessTokenRequest",
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
    });
    patchWithCleanup(download, {
        _download: async (options) => {
            expect.step(options.url);
            expect(deepEqual(options.data, {})).toBe(true);
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_kanban_record:nth-of-type(1) .o_record_selector").click({ ctrlKey: true });
    await contains(".o_kanban_record:nth-of-type(2) .o_record_selector").click({ ctrlKey: true });
    await contains("button:contains(Download)").click();
    // The request is ignored and only the spreadsheet is downloaded.
    expect.verifySteps(["/documents/content/accessTokenMyspreadsheet"]);
});

test("can open spreadsheet while multiple documents are selected along with it", async function () {
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = {
        records: [{ id: 1 }, { id: 2 }, { id: 3 }],
    };
    serverData.models["documents.document"].records = [
        { id: 1, name: "demo-workspace", type: "folder" },
        {
            name: "test-spreadsheet",
            raw: "{}",
            folder_id: 1,
            handler: "spreadsheet",
            thumbnail_status: "present",
            attachment_id: 1,
        },
        {
            folder_id: 1,
            mimetype: "image/png",
            name: "test-image-1",
            attachment_id: 2,
        },
        {
            folder_id: 1,
            mimetype: "image/png",
            name: "test-image-2",
            attachment_id: 3,
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({ serverData });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    mockActionService((action) => {
        expect.step(action.tag);
    });
    const fixture = getFixture();
    await contains(".o_kanban_record:contains('demo-workspace')").click();
    await animationFrame();

    const records = fixture.querySelectorAll(".o_kanban_record");
    await contains(records[0].querySelector(".o_record_selector")).click();
    await contains(records[1].querySelector(".o_record_selector")).click({ ctrlKey: true });
    await contains(records[2].querySelector(".o_record_selector")).click({ ctrlKey: true });
    await contains(".o_kanban_record:contains('spreadsheet') .oe_kanban_previewer").click();
    expect(".o-FileViewer").toHaveCount(0);
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("spreadsheet should be skipped while toggling the preview in the FileViewer", async function () {
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = {
        records: [
            { id: 2, name: "dogsFTW" },
            { id: 3, name: "pug" },
            { id: 4, name: "chihuahua" },
        ],
    };
    serverData.models["documents.document"].records = [
        { id: 1, name: "dogsFTW", type: "folder" },
        {
            id: 2,
            name: "dog-stats",
            raw: "{}",
            folder_id: 1,
            handler: "spreadsheet",
            thumbnail_status: "present",
            access_token: "accessTokendog-stats",
            attachment_id: 2,
        },
        {
            id: 3,
            folder_id: 1,
            mimetype: "image/png",
            name: "pug",
            access_token: "accessTokenpug",
            attachment_id: 3,
        },
        {
            id: 4,
            folder_id: 1,
            mimetype: "image/png",
            name: "chihuahua",
            access_token: "accessTokenchihuahua",
            attachment_id: 4,
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({ serverData });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_kanban_record:contains(chihuahua) div[name='document_preview']").click();
    expect(".o-FileViewer").toHaveCount(1);
    expect(".o-FileViewer-header div:first()").toHaveText("chihuahua");
    await contains(".o-FileViewer-navigation[aria-label='Next']").click();
    expect(".o-FileViewer-header div:first()").toHaveText("pug");
    await contains(".o-FileViewer-navigation[aria-label='Next']").click();
    expect(".o-FileViewer-header div:first()").toHaveText("chihuahua");
});

test("Cannot download spreadsheets", async function () {
    const serverData = getDocumentsTestServerData([
        {
            folder_id: 1,
            id: 2,
            name: "Request",
        },
        {
            attachment_id: 1,
            id: 3,
            folder_id: 1,
            name: "Binary",
        },
        {
            attachment_id: 2,
            folder_id: 1,
            handler: "spreadsheet",
            id: 4,
            name: "Spreadsheet",
        },
        {
            folder_id: 1,
            type: "url",
            id: 5,
            name: "Hurle",
        },
    ]);
    serverData.models["ir.attachment"] = {
        records: [
            { id: 1, name: "binary" },
            { id: 2, name: "spreadsheet" },
        ],
    };
    const { name: folder1Name } = serverData.models["documents.document"].records[0];
    await makeDocumentsSpreadsheetMockEnv({ serverData });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    // Folder should be downloadable
    await waitFor(".o_control_panel_actions:contains('Download')");
    await contains(`.o_kanban_record:contains('Request')`).click();
    // Request should not be downloadable
    await waitForNone(".o_control_panel_actions:contains('Download')");
    // Binary should be downloadable
    await contains(".o_kanban_record:contains('Binary')").click();
    await waitFor(".o_control_panel_actions:contains('Download')");
    // Spreadsheet should not be downloadable
    await contains(`.o_kanban_record:contains('Spreadsheet')`).click();
    await waitForNone(".o_control_panel_actions:contains('Download')");
    // Multiple documents can be downloaded
    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    await waitFor(".o_control_panel_actions:contains('Download')");
    // Button should remain even if some records are not downloadable
    await contains(`.o_kanban_record:contains('Spreadsheet')`).click({ ctrlKey: true });
    await waitFor(".o_control_panel_actions:contains('Download')");
    // Spreadsheet with url should not be downloadable
    await contains(`.o_kanban_record:contains('Spreadsheet')`).click();
    await contains(`.o_kanban_record:contains('Hurle')`).click({ ctrlKey: true });
    await waitForNone(".o_control_panel_actions:contains('Download')");
});

test("Restoring trashed XLSX without folder should not set localStorage variable to undefined", async () => {
    const spreadsheetId = 77;
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = { records: [{ id: 1 }] };
    serverData.models["documents.document"].records.push({
        id: spreadsheetId,
        name: "Trashed XLSX File",
        mimetype: XLSX_MIME_TYPES[0],
        type: "binary",
        active: false,
        attachment_id: 1,
    });

    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async (route, args) => {
            if (args.method === "action_unarchive") {
                expect.step("spreadsheet_restored");
                expect(args.model).toBe("documents.document");
                expect(args.args).toEqual([spreadsheetId]);
            }
            return null;
        },
    });

    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_search_panel_label_title:contains('Trash')").click();
    await contains(".o_kanban_record:contains('Trashed XLSX File') .oe_kanban_previewer").click();
    await contains(".modal-content .btn.btn-primary:contains('Restore')").click();

    expect.verifySteps(["spreadsheet_restored"]);

    const lsValue = browser.localStorage.getItem("searchpanel_documents_document");
    expect(lsValue).not.toBe("undefined");
});
