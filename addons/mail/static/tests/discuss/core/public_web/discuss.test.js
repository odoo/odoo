import { waitForChannels, waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { Command, patchWithCleanup, serverState, withUser } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("bus subscription updated when joining/leaving thread as non member", async () => {
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await waitForChannels([`discuss.channel_${channelId}`]);
    await click("[title='Leave Channel']");
    await click("button", { text: "Leave Conversation" });
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test("bus subscription updated when joining locally pinned thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await waitForChannels([`discuss.channel_${channelId}`]);
    await click("[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", {
        text: "Mitchell Admin",
    });
    await click("button", { text: "Invite to Channel" });
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test.skip("bus subscription kept after receiving a message as non member", async () => {
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
        name: "General",
    });
    await start();
    await Promise.all([openDiscuss(channelId), waitUntilSubscribe(`discuss.channel_${channelId}`)]);
    await withUser(johnUser, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "Hello!" });
    await tick();
    await withUser(johnUser, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Goodbye!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "Goodbye!" });
});

test("open channel in discuss from push notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await contains(".o-mail-Discuss-threadName[title='Inbox']");
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", {
            data: { action: "OPEN_CHANNEL", data: { id: channelId } },
        })
    );
    await contains(".o-mail-Discuss-threadName[title='General']");
});

test("discard push notification of already seen channel message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const [seenMessageId, unseenMessageId] = pyEnv["mail.message"].create([
        { body: "Seen", model: "discuss.channel", res_id: channelId },
        { body: "Unseen", model: "discuss.channel", res_id: channelId },
    ]);
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: seenMessageId });
    patchWithCleanup(navigator.serviceWorker, {
        controller: {
            postMessage: ({ type, payload }) => expect.step(`${type} ${payload.correlationId}`),
        },
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-Discuss-threadName[title='Inbox']");
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    for (const [correlationId, messageId] of [
        ["unseen", unseenMessageId],
        ["seen", seenMessageId],
    ]) {
        navigator.serviceWorker.dispatchEvent(
            new MessageEvent("message", {
                data: {
                    type: "notification-display-request",
                    payload: {
                        correlationId,
                        model: "discuss.channel",
                        res_id: channelId,
                        message_id: messageId,
                    },
                },
            })
        );
    }
    await expect.waitForSteps(["notification-display-response seen"]);
});
