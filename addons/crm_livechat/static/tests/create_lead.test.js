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
import { mockDate } from "@odoo/hoot-mock";

import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineCrmLivechatModels();

test("can create a lead from the thread action after the conversation ends", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: [
            Command.link(serverState.groupLivechatId),
            Command.link(serverState.groupSalesTeamId),
        ],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channel_id = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    await start();
    await openDiscuss(channel_id);
    await contains(".o-livechat-ChannelInfoList"); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Create Lead']");
    await insertText(".o-mail-ChannelCommandDialog-form input", "testlead");
    await click(".o-mail-ActionPanel button", { text: "Create Lead" });
    await contains(
        `.o-mail-NotificationMessage:text('${serverState.partnerName} created a new lead: testlead1:00 PM')`
    );
});

test("Hide Create Lead thread action and /lead command without create lead access", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: [Command.link(serverState.groupLivechatId)],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Batman" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Batcave",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header button[title='Members']");
    await contains(".o-mail-DiscussContent-header button[title='Create Lead']", { count: 0 });
    await insertText(".o-mail-Composer-input", "/");
    await contains(".o-mail-Composer-suggestion strong:text('help')");
    await contains(".o-mail-Composer-suggestion strong:text('lead')", { count: 0 });
});
