import {
    defineModels,
    mockService,
    mountWithCleanup,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";
import { mailModels, click } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { DocumentsModels, getDocumentsTestServerData } from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { basicDocumentsKanbanArch } from "./helpers/views/kanban";
import { getEnrichedSearchArch } from "./helpers/views/search";
import { WebClient } from "@web/webclient/webclient";

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
});

test("systray open documents activity loads custom action", async function () {
    const serverData = getDocumentsTestServerData([
        {
            res_model: "documents.document",
            folder_id: 1,
            id: 2,
            name: "Test Doc With Activities",
            activity_ids: [1],
            activity_user_id: serverState.userId,
        },
        {
            res_model: "documents.document",
            folder_id: 1,
            id: 3,
            name: "Test Doc Without Activities",
            activity_ids: [],
            activity_user_id: false,
        },
    ]);

    serverData.models["mail.activity"] = {
        records: [
            {
                id: 1,
                res_model: "documents.document",
                res_id: 2,
                user_id: serverState.userId,
            },
        ],
    };

    serverData.models["mail.activity.type"] = {
        records: [{ id: 1, name: "To Do" }],
    };

    DocumentsModels["DocumentsDocument"]._views = {
        kanban: basicDocumentsKanbanArch,
        search: getEnrichedSearchArch(),
    };

    mockService("action", {
        async loadAction(xmlId, context) {
            if (xmlId === "documents.document_action") {
                expect.step("load_document_action");
                return {
                    xml_id: "documents.document_action",
                    res_model: "documents.document",
                    type: "ir.actions.act_window",
                    views: [[false, "kanban"]],
                };
            }
            return super.loadAction(...arguments);
        },
        doAction(action, options) {
            if (action.xml_id === "documents.document_action") {
                expect.step("execute_document_action");
                expect(options.clearBreadcrumbs).toBe(true);
                expect(action.domain).toEqual([["activity_user_id", "=", serverState.userId]]);
            }
            return super.doAction(...arguments);
        },
    });

    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);

    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-ActivityGroup", { text: "documents.document" });
    expect.verifySteps(["load_document_action", "execute_document_action"]);
    await waitFor(".o_kanban_renderer");
    expect(".o_kanban_record:contains('Test Doc With Activities')").toHaveCount(1);
    expect(".o_kanban_record:contains('Test Doc Without Activities')").toHaveCount(0);
});
