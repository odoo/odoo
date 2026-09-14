import { WebClient } from "@web/webclient/webclient";
import { user } from "@web/core/user";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";

import {
    DocumentsModels,
    getDocumentsTestServerModelsData,
    makeDocumentRecordData,
} from "@document/../tests/helpers/data";
import { makeDocumentsMockEnv } from "@document/../tests/helpers/model";
import { basicDocumentsOperationFormArch } from "@document/../tests/helpers/views/form";
import { basicDocumentsKanbanArch } from "@document/../tests/helpers/views/kanban";
import { getEnrichedSearchArch } from "@document/../tests/helpers/views/search";

describe.current.tags("desktop");

defineModels(DocumentsModels);

defineActions([
    {
        id: 1,
        name: "Documents",
        res_model: "document.document",
        views: [[false, "kanban"]],
    },
]);
DocumentsModels.DocumentsDocument._views = {
    kanban: basicDocumentsKanbanArch,
    [["search", false]]: getEnrichedSearchArch(),
    form: `<form>
        <field name="type" invisible="1" force_save="1"/>
        <field name="active" string="Active" invisible="1"/>
        <sheet>
            <div class="oe_title">
                <label for="name"/>
                <h1><field name="name" required="True"/></h1>
            </div>
        </sheet>
    </form>`,
};
DocumentsModels.DocumentsOperation._views = { form: basicDocumentsOperationFormArch };
onRpc("/documents/touch/accessTokenRequest", () => ({}));
onRpc("/documents/touch/accessTokenDuplicateTestDoc", () => ({}));
onRpc("action_confirm", () => ({}));

test("Duplicate a document in a Newly made folder", async function () {
    const serverData = getDocumentsTestServerModelsData([
        makeDocumentRecordData(2, "Duplicate Test Doc", {
            owner_id: serverState.userId,
        }),
    ]);
    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(
        ".o_kanban_record:contains('Duplicate Test Doc') .o_record_selector",
    ).click();
    await contains(".o_dropdown_title").click();
    await contains(".o-dropdown-item .fa-clone").click();
    await animationFrame();

    expect(".btn-primary:contains('Duplicate in My Drive')").toHaveCount(1);
    expect(".btn-secondary:contains('Create a folder in My Drive')").toHaveCount(1);

    await contains(".o_widget_documents_operation_new_folder .btn-secondary").click();
    await contains(".o_input").edit("New Folder");
    await contains(".o_form_button_save").click();
    await animationFrame();

    expect(".btn-primary:contains('Duplicate in New Folder')").toHaveCount(1);
    expect(".btn-secondary:contains('Create a folder in New Folder')").toHaveCount(1);

    await contains(".o_widget_documents_operation_confirmation .btn-primary").click();

    await waitFor(".o_notification");
    expect(".o_notification_content").toHaveText(
        "Done. Document created in New Folder!",
    );
});

test('Internal users can always move to "My Drive"', async function () {
    const serverData = getDocumentsTestServerModelsData([
        makeDocumentRecordData(2, "Request", { owner_id: serverState.userId }),
        makeDocumentRecordData(3, "Folder 2", {
            owner_id: serverState.userId,
            type: "folder",
        }),
    ]);
    serverData["document.document"][0].user_permission = "view";
    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(".o_kanban_record:contains('Request') .o_record_selector").click();
    await contains(".o_dropdown_title").click();

    await contains(".o-dropdown-item .fa-right-to-bracket").click();
    await animationFrame();
    expect(".btn-primary:contains('Move to My Drive')").not.toHaveAttribute("disabled");
    expect(".btn-secondary:contains('Create a folder in My Drive')").toHaveCount(1);

    await contains(".modal-content li div span:contains('Folder 1')").click();
    await animationFrame();
    expect(".btn-primary:contains('Insufficient access to Folder 1')").toHaveAttribute(
        "disabled",
    );
    expect(".btn-secondary:contains('Create a folder in Folder 1')").toHaveCount(0);

    await contains(".modal-content li div span:contains('Folder 2')").click();
    await animationFrame();
    expect(".btn-primary:contains('Move to Folder 2')").not.toHaveAttribute("disabled");
    expect(".btn-secondary:contains('Create a folder in Folder 2')").toHaveCount(1);
});

test("Portal user without edit folder has no Move button", async function () {
    const serverData = getDocumentsTestServerModelsData([
        makeDocumentRecordData(2, "Request", {
            folder_id: 1,
            owner_id: serverState.userId,
        }),
    ]);
    serverData["document.document"][0].user_permission = "view";
    patchWithCleanup(user, {
        hasGroup: (group) => group === "base.group_portal",
    });
    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(".o_kanban_record:contains('Request') .o_record_selector").click();
    await contains(".o_dropdown_title").click();
    await waitFor(".o-dropdown-item");
    expect(".o-dropdown-item .fa-right-to-bracket").toHaveCount(0);
});

test("Portal user with any edit folder has the Move button", async function () {
    const serverData = getDocumentsTestServerModelsData([
        makeDocumentRecordData(2, "Request", { folder_id: 1, user_permission: "edit" }),
    ]);
    serverData["document.document"][0].user_permission = "edit";
    patchWithCleanup(user, {
        hasGroup: (group) => group === "base.group_portal",
    });
    patchWithCleanup(DocumentsModels.DocumentsOperation._fields, {
        destination: fields.Char({ default: "1" }),
        display_name: fields.Char({ default: "Folder 1" }),
    });
    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(".o_kanban_record:contains('Request') .o_record_selector").click();
    await contains(".o_dropdown_title").click();
    await contains(".o-dropdown-item .fa-right-to-bracket").click();
    await waitFor(".btn-primary:contains('Move to Folder 1')");
    expect(".btn-secondary:contains('Create a folder')").toHaveCount(0);
});
