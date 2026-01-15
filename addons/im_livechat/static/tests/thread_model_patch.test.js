import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

import { rpc } from "@web/core/network/rpc";
import { press } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineLivechatModels();

test("Thread name unchanged when inviting new users", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #20" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-threadName[title='Visitor #20']");
    await click("button[title='Invite People']");
    await click("input", {
        parent: [".o-discuss-ChannelInvitation-selectable", { text: "James" }],
    });
    await click("button:enabled", { text: "Invite" });
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("button[title='Members']");
    await contains(".o-discuss-ChannelMember", { text: "James" });
    await contains(".o-mail-DiscussContent-threadName[title='Visitor #20']");
});

test("Can set a custom name to livechat conversation", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #20" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-DiscussSidebar-item:contains('Visitor #20')");
    await contains(".o-mail-DiscussContent-threadName[title='Visitor #20']");
    await insertText(".o-mail-DiscussContent-threadName", "New Name", { replace: true });
    await triggerHotkey("Enter");
    await contains(".o-mail-DiscussContent-threadName[title='New Name']");
    await contains(".o-mail-DiscussSidebar-item:contains('New Name')");
});

test("Display livechat custom username if defined", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, {
        user_livechat_username: "livechat custom username",
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #20" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "hello");
    await press("Enter");
    await contains(".o-mail-Message-author", { text: "livechat custom username" });
});

test("Display livechat custom name in typing status", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    const partnerId = pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
        user_livechat_username: "livechat custom username",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await withUser(userId, () =>
        rpc("/discuss/channel/notify_typing", {
            channel_id: channelId,
            is_typing: true,
        })
    );
    await contains(".o-discuss-Typing", { text: "livechat custom username is typing..." });
});
