import {
    contains,
    defineModels,
    onRpc,
    mountWithCleanup,
    getService,
    defineActions,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";
import { describe, expect, test } from "@odoo/hoot";
import {
    DocumentsModels,
    getDocumentsTestServerModelsData,
    makeDocumentRecordData,
} from "@document/../tests/helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model.js";
import { basicDocumentsOperationFormArch } from "./helpers/views/form.js";
import { getEnrichedSearchArch } from "./helpers/views/search.js";

const commonSelectAllSteps = async () => {
    await contains(`.o_has_treeEntry .o_toggle_fold`).click();
    await contains(`.o_search_panel_label[data-tooltip="Folder 1"] div`).click();

    await contains(".o_pager_value").click();
    await contains("input.o_pager_value").edit("1-2");

    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_selection_box .o_select_domain`).toHaveCount(1);
    expect(`.o_selection_box`).toHaveText("2\nselected\n Select all 3");

    await contains(".o_select_domain").click();
    expect(`.o_selection_box`).toHaveText("All 3 selected");
};

const action1 = {
    id: 100,
    name: "Document",
    res_model: "document.document",
    search_view_id: [2, "some_search_view"],
    views: [[1, "list"]],
};

defineActions([action1]);

const actionSelector =
    ".o_control_panel_actions .o_cp_action_menus .o_dropdown_title:contains('Actions')";

const prepareSelectAllActionDataViews = () => {
    const serverData = getDocumentsTestServerModelsData([
        makeDocumentRecordData(2, "Request", {
            folder_id: 1,
            user_permission: "edit",
        }),
        makeDocumentRecordData(3, "Binary", {
            attachment_id: 1,
            folder_id: 1,
            user_permission: "edit",
        }),
        makeDocumentRecordData(4, "Binary 2", {
            attachment_id: 1,
            folder_id: 1,
            user_permission: "edit",
        }),
    ]);

    serverData["ir.attachment"] = [{ id: 1, name: "binary" }];

    DocumentsModels.DocumentsDocument._views["list,1"] =
        `<list js_class="documents_list">
                  <field name="name"/>
                  <field name="folder_id"/>
                  <field name="attachment_id" column_invisible="1"/>
                  <field name="user_permission" column_invisible="1"/>
                  <field name="active" column_invisible="1"/>
              </list>`;
    DocumentsModels.DocumentsDocument._views["search,2"] = getEnrichedSearchArch();
    DocumentsModels.DocumentsOperation._views = {
        form: basicDocumentsOperationFormArch,
    };
    return serverData;
};

describe.current.tags("desktop");
defineModels({ ...DocumentsModels });

test("Selected all records from current page are copied correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    onRpc("action_confirm", () => ({}));
    onRpc("document.operation", "web_save", ({ args }) => {
        expect(args[1].document_ids.map((d) => d[1])).toEqual([2, 3, 4]);
        expect.step("Document Copied");
    });

    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await commonSelectAllSteps();

    await contains(actionSelector).click();
    await contains(".o_menu_item.dropdown-item .fa-clone").click();
    await contains(
        `.modal-content > .modal-body .o_search_panel_label[data-tooltip="Folder 1"] div`,
    ).click();
    await contains(
        ".modal-content > .modal-footer > .o_widget_documents_operation_confirmation button",
    ).click();
    expect.verifySteps(["Document Copied"]);
});

test("Selected all records from current page are download correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    onRpc("/documents/zip", async (request) => {
        const body = await request.formData();
        expect(body.get("file_ids")).toEqual("3,4");
        expect.step("Documents downloaded");
        return new Blob([]);
    });
    await makeDocumentsMockEnv({
        serverData,
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await commonSelectAllSteps();
    await contains(".o_control_panel_actions button:contains('Download')").click();
    expect.verifySteps(["Documents downloaded"]);
});

test("Selected all records from current page are deleted correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    serverData["document.document"].forEach((record) => {
        if (record.type !== "folder") {
            record.active = false;
        }
    });
    onRpc("document.document", "unlink", ({ args }) => {
        expect(args[0]).toEqual([2, 3, 4]);
        expect.step("Document deleted");
    });
    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await contains(`.o_search_panel_label[data-tooltip="Trash"] div`).click();

    await contains(".o_pager_value").click();
    await contains("input.o_pager_value").edit("1-2");

    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_selection_box .o_select_domain`).toHaveCount(1);
    expect(`.o_selection_box`).toHaveText("2\nselected\n Select all 3");

    await contains(".o_select_domain").click();
    expect(`.o_selection_box`).toHaveText("All 3 selected");
    await contains(actionSelector).click();
    await contains(".o_menu_item.dropdown-item .fa-trash-can").click();

    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["Document deleted"]);
});

test("Selected all records from current page are archived/restore correctly", async function () {
    const serverData = prepareSelectAllActionDataViews();
    onRpc("document.document", "action_archive", ({ args }) => {
        expect(args[0]).toEqual([2, 3, 4]);
        expect.step("Document archived");
    });
    onRpc("document.document", "action_unarchive", ({ args }) => {
        expect(args[0]).toEqual([2, 3, 4]);
        expect.step("Document restored");
    });
    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(action1.id);

    await commonSelectAllSteps();
    await contains(actionSelector).click();

    await contains(".o_menu_item.dropdown-item .fa-trash-can").click();
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    expect.verifySteps(["Document archived"]);

    await contains(`.o_search_panel_label[data-tooltip="Trash"] div`).click();
    await contains(`thead .o_list_record_selector input`).click();
    expect(`.o_selection_box .o_select_domain`).toHaveCount(1);
    expect(`.o_selection_box`).toHaveText("2\nselected\n Select all 3");

    await contains(".o_select_domain").click();
    expect(`.o_selection_box`).toHaveText("All 3 selected");
    await contains(actionSelector).click();
    await contains(".o_menu_item.dropdown-item .fa-trash-arrow-up").click();
    expect.verifySteps(["Document restored"]);
});
