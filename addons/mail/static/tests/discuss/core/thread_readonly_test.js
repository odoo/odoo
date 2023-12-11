/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("Access channels without memberhip (readonly)");

QUnit.test("Readonly threads are not accessible by default", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Channel without members",
        channel_member_ids: [],
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains("input[title='Inbox']");
    await contains(".o-mail-Thread-empty", { text: "Congratulations, your inbox is empty" });
});

QUnit.test("Features are limited if the user is not a member of the channel", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const internalUserId = pyEnv["res.users"].create({ name: "James" });
    const internalPartnerId = pyEnv["res.partner"].create({
        name: "James",
        user_ids: [internalUserId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Visitor",
        channel_member_ids: [
            Command.create({ partner_id: internalPartnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "Welcome!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-04-03 08:15:04",
        author_id: internalPartnerId,
    });

    const discussContext = { context: { allowReadonly: true } };
    const { env, openDiscuss } = await start({ discuss: discussContext });
    openDiscuss(channelId);
    // Subscribed to new messages bus notifications but not UI alerts are displayed.
    pyEnv.withUser(internalUserId, () => {
        env.services.rpc("/mail/message/post", {
            post_data: { body: "How is your day ?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
    });
    await contains(".o-mail-Message-body", { text: "How is your day ?" });
    await contains(".o_notification", { count: 0 });
    // Some header menus and message actions disabled
    await contains(".o-mail-Composer", { count: 0 });
    await contains(".o-mail-Message-actions", { count: 0 });
    await contains("button[name='call']", { count: 0 });
    await contains("button[name='add-users']", { count: 0 });
    await contains("button[name='settings']", { count: 0 });
    // Can browse attachments but not interact with
    await click("button[name='attachments']");
    await contains(".o-mail-ActionPanel .form-switch", { count: 0 });
    // Can browse channel members but not invite anyone
    await click("button[name='member-list']");
    await contains(".o-discuss-ChannelMember", { count: 2 });
    await contains("button", { count: 0, text: "Invite a User" });
    // Can browse pinned messages but not unpin them
    await click("button[name='pinned-messages']");
    await contains(".o-mail-MessageCardList");
    await contains("button[title='unpin']", { count: 0 });
    // Conversation is only pinned while opened
    await contains(".o-mail-DiscussSidebar-item", { text: "Visitor" });
    await click(".o-mail-DiscussSidebar-item", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebar-item", { count: 0, text: "Visitor" });
});
