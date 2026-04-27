import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import {
    contains,
    defineModels,
    mountView,
    onRpc,
    patchWithCleanup,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";

import {
    DocumentsModels,
    getBasicPermissionPanelData,
    getDocumentsTestServerData,
} from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { basicDocumentsListArch } from "./helpers/views/list";
import { getEnrichedSearchArch } from "./helpers/views/search";

describe.current.tags("desktop");

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
});

test("Open share with view user_permission", async function () {
    onRpc("/documents/touch/accessTokenFolder1", () => true);
    const serverData = getDocumentsTestServerData();
    const { id: folder1Id, name: folder1Name } = serverData.models["documents.document"].records[0];
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("Document url copied");
            expect(url).toBe("https://localhost:8069/odoo/documents/accessTokenFolder1");
        },
    });
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(folder1Id);
                expect.step("permission_panel_data");
                return getBasicPermissionPanelData({
                    access_url: "https://localhost:8069/odoo/documents/accessTokenFolder1",
                });
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    await contains(`.o_data_row:contains(${folder1Name}) .o_list_record_selector`).click();
    await contains("button:contains(Share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "Document url copied"]);
});

test("company_id field visibility for internal in multicompany", async function () {
    serverState.companies = [
        { id: 1, name: "Company 1", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Company 2", sequence: 2, parent_id: false, child_ids: [] },
    ];
    const serverData = getDocumentsTestServerData();
    await makeDocumentsMockEnv({ serverData });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
        context: {
            allowed_company_ids: [1, 2],
        },
    });
    expect("thead th[data-name='company_id']").toHaveCount(1);
});

test("company_id field visibility for portal in multicompany", async function () {
    serverState.companies = [
        { id: 1, name: "Company 1", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Company 2", sequence: 2, parent_id: false, child_ids: [] },
    ];
    const testUserGroups = ["base.group_portal", "base.group_multi_company"];
    // We need to do this here and not on the model because has_group("base.group_user")
    // is already in cache before the model method is called the first time.
    patchWithCleanup(user, {
        hasGroup: (group) => testUserGroups.includes(group),
    });
    const serverData = getDocumentsTestServerData();
    const currentUser = serverData.models["res.users"].records.find(
        (u) => u.id === serverState.userId
    );
    // Sync server data for consistency even if it is not really used.
    Object.assign(currentUser, { groups_id: [], share: true });
    await makeDocumentsMockEnv({ serverData });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
        context: {
            allowed_company_ids: [1, 2],
        },
    });
    expect("thead th[data-name='company_id']").toHaveCount(0);
});

test("file sharing via link with multiple subfolders", async function () {
    let accessFolder1 = false;
    let accessFolder2 = false;
    let addFolder4 = false;
    onRpc("/documents/touch/accessTokenFolder1", () => {
        expect.step("touch 1");
        accessFolder1 = true;
        return { reload: true };
    });
    onRpc("/documents/touch/accessTokenFolder2", () => {
        expect.step("touch 2");
        accessFolder2 = true;
        return { reload: true };
    });
    onRpc("/documents/touch/accessTokenFolder3", () => {
        return { reload: true };
    });
    onRpc("/documents/touch/accessTokenFolder4", () => {
        return { reload: true };
    });

    // Set active true/false to control the folders display
    const folder2 = {
        id: 2,
        name: "Folder 2",
        type: "folder",
        is_folder: true,
        folder_id: 1,
        access_token: "accessTokenFolder2",
        active: false,
    };
    const folder3 = {
        id: 3,
        name: "Folder 3",
        type: "folder",
        is_folder: true,
        folder_id: 2,
        access_token: "accessTokenFolder3",
        active: false,
    };
    const folder4 = {
        id: 4,
        name: "Folder 4",
        type: "folder",
        is_folder: true,
        folder_id: 2,
        access_token: "accessTokenFolder4",
        active: false,
    };
    const serverData = getDocumentsTestServerData([folder2, folder3, folder4]);

    const docEnv = await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (["web_search_read", "search_panel_select_range"].includes(args.method)) {
                folder2.active = accessFolder1;
                folder3.active = accessFolder2;
                if (addFolder4) {
                    folder4.active = accessFolder2;
                }
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    const docService = docEnv.services["document.document"];
    // Avoid logAccess 1000ms debounce timer
    patchWithCleanup(docService, {
        logAccess: (token) => docService._logAccess(token),
    });
    await mountView({
        type: "list",
        resModel: "documents.document",
        arch: basicDocumentsListArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(`.o_search_panel_label[data-tooltip="Shared with me"] .o_toggle_fold`).click();
    await contains(`.o_data_row .o_field_cell[name="name"]:contains("Folder 1")`).click();
    await contains(`.o_data_row .o_field_cell[name="name"]:contains("Folder 2")`).click();
    await contains(`.o_data_row .o_field_cell[name="name"]:contains("Folder 3")`).click();
    expect.verifySteps(["touch 1", "touch 2"]);

    expect(`.o_search_panel_label[data-tooltip="Folder 4"]`).toHaveCount(0);
    // New sub-folder added without reloading
    addFolder4 = true;
    await contains(`.o_search_panel_label_title:contains("Folder 2")`).click();
    expect(`.o_search_panel_label[data-tooltip="Folder 4"]`).toHaveCount(0);
    await contains(`.o_data_row .o_field_cell[name="name"]:contains("Folder 4")`).click();
    expect(`.o_search_panel_label[data-tooltip="Folder 4"]`).toHaveCount(1);
    expect.verifySteps(["touch 2"]);
});
