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
import { EventBus } from "@odoo/owl";
import { Command, patchWithCleanup, withUser, mockService } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

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
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
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
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
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
    patchWithCleanup(window.navigator, {
        serviceWorker: Object.assign(new EventBus(), {
            register: () => Promise.resolve(),
            ready: Promise.resolve(),
        }),
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-DiscussContent-threadName[title='Inbox']");
    browser.navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", {
            data: { action: "OPEN_CHANNEL", data: { id: channelId } },
        })
    );
    await contains(".o-mail-DiscussContent-threadName[title='General']");
});

test("notify message to user as non member", async () => {
    patchWithCleanup(window, {
        Notification: class Notification {
            static get permission() {
                return "granted";
            }
            constructor() {
                expect.step("push notification");
            }
            addEventListener() {}
        },
    });
    mockService("multi_tab", { isOnMainTab: () => true });
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
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
    expect.verifySteps(["push notification"]);
});
