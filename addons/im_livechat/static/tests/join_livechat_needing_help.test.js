import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import {
    click,
    contains,
    openDiscuss,
    openFormView,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";

<<<<<<< db80e85e2b89b55dd78ab180ba14663d817c3f4b
import { Deferred } from "@web/core/utils/concurrency";
import { Command, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
||||||| c758b93a57cd98ab76c26c03bd0097f2eef50961
import { Deferred } from "@web/core/utils/concurrency";
import { Command, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";
=======
import {
    Command,
    getService,
    onRpc,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";
import { Deferred } from "@web/core/utils/concurrency";
>>>>>>> b7f3f178138da3d91ff14f5acaf5724c51932ca9

defineLivechatModels();
describe.current.tags("desktop");

<<<<<<< db80e85e2b89b55dd78ab180ba14663d817c3f4b
||||||| c758b93a57cd98ab76c26c03bd0097f2eef50961
test("Show looking for help in the sidebar while active or still seeking help", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    const bobChannelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
        livechat_status: "need_help",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await waitForChannels([`discuss.channel_${bobChannelId}`]);
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "in_progress",
    });
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob", count: 0 });
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "need_help",
    });
    await click(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "bob" });
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "in_progress",
    });
    await contains(".o-livechat-LivechatStatusSelection .o-inProgress.active");
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await click(".o-mail-Mailbox[data-mailbox-id=starred");
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob", count: 0 });
});

=======
test("Show looking for help in the sidebar while active or still seeking help", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    const bobChannelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
        livechat_status: "need_help",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await waitForChannels([`discuss.channel_${bobChannelId}`]);
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "in_progress",
    });
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob", count: 0 });
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "need_help",
    });
    await click(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "bob" });
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "in_progress",
    });
    await contains(".o-livechat-LivechatStatusSelection .o-inProgress.active");
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await click(".o-mail-Mailbox[data-mailbox-id=starred");
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob", count: 0 });
});

test("Do not auto-open chat window on new message when locally pinned", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    setupChatHub({
        folded: [
            pyEnv["discuss.channel"].create({
                name: "General",
                channel_type: "channel",
            }),
        ],
        opened: [
            pyEnv["discuss.channel"].create({
                name: "Support",
                channel_type: "channel",
            }),
        ],
    });
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    const bobChannelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
        livechat_status: "need_help",
    });
    await start();
    getService("bus_service").subscribe("discuss.channel/new_message", () =>
        expect.step("discuss.channel/new_message")
    );
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await waitForChannels([`discuss.channel_${bobChannelId}`]);
    await withUser(serverState.userId, async () => {
        await rpc("/mail/message/post", {
            post_data: {
                body: "Hello, how can I help?",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: bobChannelId,
            thread_model: "discuss.channel",
        });
    });
    await contains(".o-mail-Message", { text: "Hello, how can I help?" });
    await expect.waitForSteps(["discuss.channel/new_message"]);
    await openFormView("res.partner", bobPartnerId);
    await contains(".o-mail-ChatBubble");
    await contains(".o-mail-ChatBubble[name=General]");
    await contains(".o-mail-ChatBubble", { count: 0, text: "bob" });
    await contains(".o-mail-ChatWindow", { text: "Support" });
    await contains(".o-mail-ChatWindow", { count: 0, text: "bob" });
});

>>>>>>> b7f3f178138da3d91ff14f5acaf5724c51932ca9
test("Show join button when help is required and self is not a member", async () => {
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    const channel = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
        livechat_status: "need_help",
    });
    await start();
    await openDiscuss(channel);
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "Looking for help" });
    await click("button[name='join-channel']");
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "In progress" });
    await contains("button[name='join-channel']", { count: 0 });
    await click("button", { text: "Looking for help" });
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "Looking for help" });
    // Now that we are members, the button is not shown, even if help is required.
    await contains("button[name='join-channel']", { count: 0 });
});

test("Show notification when joining a channel that already received help", async () => {
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    // Simulate another agent attempting to join the channel to provide help at the same time,
    // but succeeding just before the current agent (server returns false when it happens).
    onRpc("discuss.channel", "livechat_join_channel_needing_help", () => false);
    const channel = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
        livechat_status: "need_help",
    });
    const env = await start();
    patchWithCleanup(env.services.notification, {
        add: (message, options) => expect.step(`${options.type} - ${message}`),
    });
    await openDiscuss(channel);
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "Looking for help" });
    await click("button[name='join-channel']");
    expect.waitForSteps(["warning - Someone has already joined this conversation"]);
});

test("Hide 'help already received' notification when channel is not visible", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    // Simulate another agent attempting to join the channel to provide help at the same time,
    // but succeeding just before the current agent (server returns false when it happens).
    let canRespondDeferred;
    onRpc("discuss.channel", "livechat_join_channel_needing_help", async () => {
        await canRespondDeferred;
        return false;
    });
    const channel = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
        livechat_status: "need_help",
    });
    const env = await start();
    patchWithCleanup(env.services.notification, {
        add: (message, options) => expect.step(`${options.type} - ${message}`),
    });
    await openDiscuss(channel);
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "Looking for help" });
    await click("button[name='join-channel']");
    expect.waitForSteps(["warning - Someone has already joined this conversation"]);
    canRespondDeferred = new Deferred();
    await click("button[name='join-channel']");
    await click(".o-mail-DiscussSidebar-item", { text: "Inbox" });
    await contains(".o-mail-DiscussContent-threadName[title='Inbox']");
    canRespondDeferred.resolve();
    await tick();
    await expect.waitForSteps([]);
});
