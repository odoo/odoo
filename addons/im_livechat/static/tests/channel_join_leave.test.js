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
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { rpc } from "@web/core/network/rpc";

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
        create_uid: serverState.publicUserId,
    });
    await start();
    await openDiscuss();
    await click("[title='Leave HR']", {
        parent: [".o-mail-DiscussSidebarCategory-livechat", { text: "HR" }],
    });
    await click("[title='Join HR']", {
        parent: [".o-mail-DiscussSidebarCategory-livechat", { text: "HR" }],
    });
    await click("[title='Leave Channel']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "Visitor" }],
    });
    await click("button:contains(Leave Conversation)");
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

test("from chat window", async () => {
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
            Command.create({ partner_id: serverState.partnerId, fold_state: "open" }),
            Command.create({ guest_id: guestId }),
        ],
        livechat_active: true,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    await start();
    await contains(".o-mail-ChatWindow");
    await click("button[title*='Close Chat Window']");
    await click("button:contains('Yes, leave conversation')");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o_notification:contains(You left Visitor)");
});

test("visitor leaving ends the livechat conversation", async () => {
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
    const channel_id = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, fold_state: "open" }),
            Command.create({ guest_id: guestId }),
        ],
        livechat_active: true,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    await start();
    await contains(".o-mail-ChatWindow");
    // simulate visitor leaving
    await withGuest(guestId, () => rpc("/im_livechat/visitor_leave_session", { channel_id }));
    await contains("span", { text: "This livechat conversation has ended" });
    await click("button[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
});
