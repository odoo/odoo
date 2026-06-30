import { waitForChannels } from "@bus/../tests/bus_test_helpers";

import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { LFH_UNSUBSCRIBE_DELAY } from "@im_livechat/core/public_web/discuss_app_model_patch";

import {
    click,
    contains,
    openDiscuss,
    openFormView,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { advanceTime, describe, expect, test } from "@odoo/hoot";
import { tick, waitFor } from "@odoo/hoot-dom";

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

defineLivechatModels();
describe.current.tags("desktop");

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
    await contains(".o-mail-DiscussSidebarCategory-livechatNeedHelp .oi-chevron-down");
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await waitForChannels(["im_livechat.looking_for_help"]);
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
    await waitForChannels([`discuss.channel_${bobChannelId}`]);
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "in_progress",
    });
    await contains(".o-livechat-LivechatStatusSelection .o-inProgress.active");
    await waitForChannels([`discuss.channel_${bobChannelId}`]);
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob" });
    await click(".o-mail-Mailbox[data-mailbox-id=starred");
    await contains(".o-mail-DiscussSidebarChannel", { text: "bob", count: 0 });
    await waitForChannels([`discuss.channel_${bobChannelId}`], { operation: "delete" });
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
    await contains(".o-mail-DiscussSidebarCategory-livechatNeedHelp .oi-chevron-down");
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

test("Enable/disable looking for help when category is opened/folded", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    localStorage.setItem("discuss_sidebar_category_im_livechat.category_need_help_open", false);
    await start();
    patchWithCleanup(getService("bus_service"), {
        addChannel: (channelName) => {
            if (channelName === "im_livechat.looking_for_help") {
                expect.step(`addChannel - ${channelName}`);
            }
        },
        deleteChannel: (channelName) => {
            if (channelName === "im_livechat.looking_for_help") {
                expect.step(`deleteChannel - ${channelName}`);
            }
        },
    });
    onRpc("/mail/data", async (req) => {
        const { params } = await req.json();
        if (params.fetch_params.includes("/im_livechat/looking_for_help")) {
            expect.step("fetch looking_for_help");
        }
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-livechatNeedHelp .oi-chevron-right");
    await expect.waitForSteps([]);
    await click(".o-mail-DiscussSidebarCategory-livechatNeedHelp button");
    await contains(".o-mail-DiscussSidebarCategory-livechatNeedHelp .oi-chevron-down");
    await expect.waitForSteps([
        "addChannel - im_livechat.looking_for_help",
        "fetch looking_for_help",
    ]);
    await click(".o-mail-DiscussSidebarCategory-livechatNeedHelp button");
    await contains(".o-mail-DiscussSidebarCategory-livechatNeedHelp .oi-chevron-right");
    await expect.waitForSteps([]);
    await advanceTime(LFH_UNSUBSCRIBE_DELAY + 1000);
    await expect.waitForSteps(["deleteChannel - im_livechat.looking_for_help"]);
    await click(".o-mail-DiscussSidebarCategory-livechatNeedHelp button");
    await contains(".o-mail-DiscussSidebarCategory-livechatNeedHelp .oi-chevron-down");
    await expect.waitForSteps([
        "addChannel - im_livechat.looking_for_help",
        "fetch looking_for_help",
    ]);
});

test("Show join button when help is required and self is not a member", async () => {
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
    const channel = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
        livechat_status: "need_help",
    });
    await start();
    await openDiscuss(channel);
    await contains(".o-mail-DiscussSidebarCategory-livechatNeedHelp .oi-chevron-down");
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "Looking for help" });
    await click("button[name='join-livechat-needing-help']");
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "In progress" });
    await contains("button[name='join-livechat-needing-help']", { count: 0 });
    await click(".o-livechat-LivechatStatusSelection button", { text: "Looking for help" });
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "Looking for help" });
    // Now that we are members, the button is not shown, even if help is required.
    await contains("button[name='join-livechat-needing-help']", { count: 0 });
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
    await click("button[name='join-livechat-needing-help']");
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
    await click("button[name='join-livechat-needing-help']");
    expect.waitForSteps(["warning - Someone has already joined this conversation"]);
    canRespondDeferred = new Deferred();
    await click("button[name='join-livechat-needing-help']");
    await click(".o-mail-DiscussSidebar-item", { text: "Inbox" });
    await contains(".o-mail-DiscussContent-threadName[title='Inbox']");
    canRespondDeferred.resolve();
    await tick();
    await expect.waitForSteps([]);
});

test("Expertise matching hint is shown in the sidebar when chat is looking for help", async () => {
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
    const janePartnerId = pyEnv["res.partner"].create({
        name: "jane",
        user_ids: [Command.create({ name: "jane" })],
    });
    const expertiseIds = pyEnv["im_livechat.expertise"].create([{ name: "pricing" }]);
    pyEnv["res.users"].write([serverState.userId], { livechat_expertise_ids: expertiseIds });
    pyEnv["discuss.channel"].create([
        {
            channel_type: "livechat",
            channel_member_ids: [Command.create({ partner_id: bobPartnerId })],
            livechat_status: "need_help",
            livechat_expertise_ids: expertiseIds,
        },
        {
            channel_type: "livechat",
            channel_member_ids: [Command.create({ partner_id: janePartnerId })],
            livechat_status: "need_help",
        },
    ]);
    await start();
    await openDiscuss();
    await waitFor(
        ".o-mail-DiscussSidebarChannel:text(bob):has([title='Relevant to your expertise'])"
    );
    await waitFor(".o-mail-DiscussSidebarChannel:text(jane)");
    await waitFor(
        ".o-mail-DiscussSidebarChannel:text(jane):not(:has([title='Relevant to your expertise']))"
    );
});
