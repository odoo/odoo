import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineCrmModels } from "@crm/../tests/crm_test_helpers";

describe.current.tags("desktop");
defineCrmModels();

test("Can create lead from thread action", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Create lead']");
    await insertText(".o-create-lead-panel input", "testlead");
    await click(".o-mail-ActionPanel button", { text: "Create" });
    await contains(".o_mail_notification", { text: "Create a new lead: testlead" });
});
