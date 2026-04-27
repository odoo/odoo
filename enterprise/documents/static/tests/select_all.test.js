import {
    contains,
    defineModels,
    onRpc,
    mountWithCleanup,
    getService,
    getPagerLimit,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";
import { describe, expect, test } from "@odoo/hoot";
import { DocumentsModels, getDocumentsTestServerData, DocumentsDocument } from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { getEnrichedSearchArch } from "./helpers/views/search";

// Common Steps to select all files for control panel actions
const commonSelectAllSteps = async () => {
    // Select Folder 1
    await contains(`.o_has_treeEntry .o_toggle_fold`).click();
    await contains(`.o_search_panel_label[data-tooltip="Folder 1"] div`).click();

    // reduce limit to 2
    await contains(".o_pager_value").click();
    await contains("input.o_pager_value").edit("1-2");

    // Select records on current page
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("2\nselected\n Select all 3");

    // Select all records with domain selector
    await contains(".o_list_select_domain").click();
    expect(`.o_list_selection_box`).toHaveText("All 3 selected");
};

const action1 = {
    id: 100,
    name: "Document",
    res_model: "documents.document",
    search_view_id: [2, "some_search_view"],
    views: [[1, "list"]],
};

// Prepare data to perform select all actions
const prepareSelectAllActionDataViews = () => {
    const serverData = getDocumentsTestServerData([
        {
            folder_id: 1,
            id: 2,
            name: "Request",
            user_permission: "edit",
        },
        {
            attachment_id: 1,
            folder_id: 1,
            id: 3,
            name: "Binary",
            user_permission: "edit",
        },
        {
            attachment_id: 1,
            folder_id: 1,
            id: 4,
            name: "Binary 2",
            user_permission: "edit",
        },
    ]);

    serverData.models["ir.attachment"] = {
        records: [{ id: 1, name: "binary" }],
    };

    DocumentsDocument._views["list,1"] = `<list js_class="documents_list">
                  <field name="name"/>
                  <field name="folder_id"/>
                  <field name="user_permission" invisible="1"/>
                  <field name="active" invisible="1"/>
              </list>`;
    DocumentsDocument._views["search,2"] = getEnrichedSearchArch();

    serverData.actions = { action1 };

    return serverData;
};

describe.current.tags("desktop");
defineModels({ ...DocumentsModels });

test("Selected all records from current page are copied correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "copy") {
                expect(args.args[0]).toEqual([2, 3, 4]);
                expect.step("Document Copied");
                return;
            }
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await commonSelectAllSteps();

    await contains(".o_documents_action_dropdown button").click();
    await contains(".o_documents_action_dropdown .dropdown-menu .dropdown-item .fa-copy").click();
    expect.verifySteps(["Document Copied"]);
    expect(getPagerLimit()).toEqual(6);
});

test("Selected all records from current page are download correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    onRpc("/documents/zip", async (request) => {
        const body = await request.formData();
        expect(body.get("file_ids")).toEqual("2,3,4");
        expect.step("Documents downloaded");
        return new Blob([]);
    });
    await makeDocumentsMockEnv({
        serverData,
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await commonSelectAllSteps();
    await contains(".o_documents_download_button").click();
    expect.verifySteps(["Documents downloaded"]);
});

test("Selected all records from current page are deleted correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    serverData.models["documents.document"].records.forEach((record) => {
        if (record.type !== "folder") {
            record.active = false;
        }
    });
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "unlink") {
                expect(args.args[0]).toEqual([2, 3, 4]);
                expect.step("Document deleted");
                return;
            }
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await contains(`.o_search_panel_label[data-tooltip="Trash"] div`).click();

    await contains(".o_pager_value").click();
    await contains("input.o_pager_value").edit("1-2");

    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("2\nselected\n Select all 3");

    await contains(".o_list_select_domain").click();
    expect(`.o_list_selection_box`).toHaveText("All 3 selected");
    await contains(".o_documents_action_dropdown button").click();
    await contains(".o_documents_action_dropdown .dropdown-menu .dropdown-item .fa-trash").click();
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["Document deleted"]);
});

test("Selected all records from current page are archived/restore correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "action_archive") {
                expect(args.args[0]).toEqual([2, 3, 4]);
                expect.step("Document archived");
                return;
            }
            if (args.method === "action_unarchive") {
                expect(args.args[0]).toEqual([2, 3, 4]);
                expect.step("Document restored");
                return;
            }
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await commonSelectAllSteps();
    await contains(".o_documents_action_dropdown button").click();

    await contains(".o_documents_action_dropdown .dropdown-menu .dropdown-item .fa-trash").click();
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["Document archived"]);

    await contains(`.o_search_panel_label[data-tooltip="Trash"] div`).click();
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_list_selection_box .o_list_select_domain`).toHaveCount(1);
    expect(`.o_list_selection_box`).toHaveText("2\nselected\n Select all 3");

    await contains(".o_list_select_domain").click();
    expect(`.o_list_selection_box`).toHaveText("All 3 selected");
    await contains(".o_documents_action_dropdown button").click();
    await contains(
        ".o_documents_action_dropdown .dropdown-menu .dropdown-item .fa-history"
    ).click();
    expect.verifySteps(["Document restored"]);
});
