import { waitForChannels } from "@bus/../tests/bus_test_helpers";

import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import {
    click,
    contains,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { tick, waitFor } from "@odoo/hoot-dom";

import { Command, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";

defineLivechatModels();
describe.current.tags("desktop");

test("Show looking for help in the sidebar", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
        notification_type: "inbox",
    });
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    const bobChannelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [],
        livechat_status: "need_help",
    });
    pyEnv["discuss.channel.member"].create({
        channel_id: bobChannelId,
        partner_id: bobPartnerId,
        livechat_member_type: "visitor",
    });
    await start();
    await openDiscuss("tab:livechat");
    await click("button:text('Help Needed')");
    await contains(".o-mail-MessagingMenuItem:has(:text(bob))");
    await waitForChannels(["im_livechat.looking_for_help"]);
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "in_progress",
    });
    await contains(".o-mail-MessagingMenuItem:has(:text(bob))", { count: 0 });
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "need_help",
    });
    await click(".o-mail-NotificationItem:has(:text(bob))");
    await contains(".o-mail-NotificationItem.o-active:has(:text(bob))");
    await waitForChannels([`discuss.channel_${bobChannelId}`]);
    await rpc("/im_livechat/session/update_status", {
        channel_id: bobChannelId,
        livechat_status: "in_progress",
    });
    await contains(".o-livechat-LivechatStatusSelection .o-inProgress.active");
    await click("button:text('Help Needed')");
    await contains(".o-mail-MessagingMenuItem:has(:text(bob))");
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
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "Looking for help" });
    await click("button[name='join-channel']");
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "In progress" });
    await contains("button[name='join-livechat-needing-help']", { count: 0 });
    await click(".o-livechat-LivechatStatusSelection button", { text: "Looking for help" });
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
    await click("[title='Chat Actions']");
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
    let joinChannelPromise;
    onRpc("discuss.channel", "livechat_join_channel_needing_help", async () => {
        await joinChannelPromise;
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
    await tick();
    expect.waitForSteps(["warning - Someone has already joined this conversation"]);
    const { promise, resolve: resolveJoinChannel } = Promise.withResolvers();
    joinChannelPromise = promise;
    await click("button[name='join-channel']");
    await openFormView("res.partner", serverState.partner_id);
    resolveJoinChannel();
    await tick();
    expect.waitForSteps([]);
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
    const [bobChannelId, janeChannelId] = pyEnv["discuss.channel"].create([
        {
            channel_type: "livechat",
            channel_member_ids: [],
            livechat_status: "need_help",
            livechat_expertise_ids: expertiseIds,
        },
        {
            channel_type: "livechat",
            channel_member_ids: [],
            livechat_status: "need_help",
        },
    ]);
    pyEnv["discuss.channel.member"].create([
        { channel_id: bobChannelId, partner_id: bobPartnerId, livechat_member_type: "visitor" },
        { channel_id: janeChannelId, partner_id: janePartnerId, livechat_member_type: "visitor" },
    ]);
    await start();
    await openDiscuss("tab:livechat");
    await click("button:text('Help needed')");
    await waitFor(".o-mail-MessagingMenuItem:has(:text(bob)) [title='Relevant to your expertise']");
    await waitFor(".o-mail-MessagingMenuItem:has(:text(jane))");
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(jane)):not(:has([title='Relevant to your expertise']))"
    );
});
