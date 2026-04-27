import {
    contains,
    defineModels,
    getService,
    mountWithCleanup,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";
import { click, mailModels, contains as mailContains } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { DocumentsModels, getDocumentsTestServerData } from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { basicDocumentsKanbanArch } from "./helpers/views/kanban";
import { getEnrichedSearchArch } from "./helpers/views/search";
import { WebClient } from "@web/webclient/webclient";
import { basicDocumentsListArch } from "./helpers/views/list";

describe.current.tags("desktop");

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
});
const ACTION_1_ID = 100;

const getServerData = () => {
    const serverData = getDocumentsTestServerData([
        {
            res_model: "documents.document",
            folder_id: 1,
            id: 2,
            name: "Test Doc With Notification",
        },
    ]);

    serverData.models["mail.message"] = {
        records: [
            {
                author_id: serverState.partnerId,
                body: "Howdy Neighbor",
                needaction: true,
                model: "documents.document",
                res_id: 2,
                id: 1000,
            },
        ],
    };
    serverData.models["mail.notification"] = {
        records: [
            {
                mail_message_id: 1000,
                notification_status: "sent",
                notification_type: "inbox",
                res_partner_id: serverState.partnerId,
            },
        ],
    };
    const action1 = {
        id: ACTION_1_ID,
        name: "Document",
        res_model: "documents.document",
        search_view_id: [false, "search"],
        views: [
            [false, "kanban"],
            [false, "list"],
            [false, "form"],
        ],
    };

    DocumentsModels["DocumentsDocument"]._views = {
        kanban: basicDocumentsKanbanArch,
        form: `<form>`,
        list: basicDocumentsListArch,
        search: getEnrichedSearchArch(),
    };
    serverData.actions = { action1 };
    return serverData;
};

const openNotificationToDocument = async () => {
    await click(".o-mail-DiscussSystray-class .fa-comments");
    await click(".o-mail-NotificationItem");
    await mailContains(".o-mail-ChatWindow");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Open in Documents" });
    await waitFor('.o_search_panel_category_value header.active:contains("All")');
    expect(".o_kanban_record.o_record_selected:contains('Test Doc With Notification')").toHaveCount(
        1
    );
};

test("Systray Open switches to All and selects the document", async function () {
    await makeDocumentsMockEnv({ serverData: getServerData() });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(ACTION_1_ID);
    await contains('.o_search_panel_label_title:contains("My Drive")').click();
    await waitFor('.o_search_panel_category_value header.active:contains("My Drive")');
    await openNotificationToDocument();
});

test("Systray Open opens documents on All and selects the document", async function () {
    await makeDocumentsMockEnv({ serverData: getServerData() });
    await mountWithCleanup(WebClient);
    await openNotificationToDocument();
});
