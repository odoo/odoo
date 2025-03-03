import { CrmLead } from "@crm/../tests/mock_server/mock_models/crm_lead";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";

import { describe, test } from "@odoo/hoot";

import { Command, defineModels, serverState } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineLivechatModels();
defineModels([CrmLead]);

test("can create a lead from the thread action after the conversation ends", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        groups_id: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        name: "CRM_LEAD",
        user_ids: [serverState.userId],
    });
    const channel_id = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        livechat_active: true,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    await start();
    await openDiscuss(channel_id);
    // simulate visitor leaving
    await withGuest(guestId, () => rpc("/im_livechat/visitor_leave_session", { channel_id }));
    await contains(".fw-bold", { text: "This livechat conversation has ended" });
    await click(".o-mail-Discuss-header button[title='Create lead']");
    await insertText(".o-crm_livechat-CreateLeadPanel-form input", "testlead");
    await click(".o-mail-ActionPanel button", { text: "Create" });
    await contains(".o_mail_notification", { text: "Created a new lead: testlead" });
});
