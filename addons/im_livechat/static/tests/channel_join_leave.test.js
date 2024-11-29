import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineLivechatModels();

test("from the discuss app", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        groups_id: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        name: "HR",
        user_ids: [serverState.userId],
    });
    pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await click("[title='Leave HR']", {
        parent: [".o-mail-DiscussSidebarCategory-livechat", { text: "HR" }],
    });
    await click("[title='Join HR']", {
        parent: [".o-mail-DiscussSidebarCategory-livechat", { text: "HR" }],
    });
    await click("[title='Unpin Conversation']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "Visitor" }],
    });
    await click("[title='Leave HR']", {
        parent: [".o-mail-DiscussSidebarCategory-livechat", { text: "HR" }],
    });
    await contains(".o-mail-DiscussSidebarCategory-livechat", { text: "HR", count: 0 });
});

test("from the command palette", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        groups_id: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    pyEnv["im_livechat.channel"].create({ name: "HR", user_ids: [serverState.userId] });
    await start();
    await triggerHotkey("control+k");
    await click(".o_command", { text: "Leave HR" });
    await contains(".o_notification", { text: "You left HR." });
    await contains(".o_command", { text: "HR", count: 0 });
    await triggerHotkey("control+k");
    await click(".o_command", { text: "Join HR" });
    await contains(".o_notification", { text: "You joined HR." });
});
