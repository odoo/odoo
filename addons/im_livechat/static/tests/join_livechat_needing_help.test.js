import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";

import { Deferred } from "@web/core/utils/concurrency";
import { Command, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

defineLivechatModels();
describe.current.tags("desktop");

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
    await click("button[name='join-livechat-needing-help']");
    await contains(".o-livechat-LivechatStatusSelection .active", { text: "In progress" });
    await contains("button[name='join-livechat-needing-help']", { count: 0 });
    await click("button", { text: "Looking for help" });
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
