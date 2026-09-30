import { defineCrmLivechatModels } from "@crm_livechat/../tests/crm_livechat_test_helpers";

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

describe.current.tags("desktop");
defineCrmLivechatModels();

test("can create a lead from the thread action after the conversation ends", async () => {
    const pyEnv = await startServer();
    const groupId = pyEnv["res.groups"].create({ name: "Sales Team" });
    serverState.groupSalesTeamId = groupId;
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: [Command.link(groupId)],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channel_id = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channel_id);
    await contains(".o-livechat-ChannelInfoList"); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Create Lead']");
    await insertText(".o-livechat-LivechatCommandDialog-form input", "testlead");
    await click(".o-mail-ActionPanel button", { text: "Create Lead" });
    await contains(".o_mail_notification", { text: "Created a new lead: testlead" });
});
