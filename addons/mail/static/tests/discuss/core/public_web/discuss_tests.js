/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import {
    waitForChannels,
    waitUntilSubscribe,
} from "@bus/../tests/helpers/websocket_event_deferred";

import { start } from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

import { click, contains } from "@web/../tests/utils";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("discuss");

QUnit.test("bus subscription updated when joining/leaving thread as non member", async () => {
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
        name: "General",
    });
    const { env, openDiscuss } = await start();
    await Promise.all([openDiscuss(channelId), waitForChannels([`discuss.channel_${channelId}`])]);
    await pyEnv.withUser(johnUser, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "Hey there!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await click("[title='Leave this channel']");
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

QUnit.test("bus subscription updated when joining locally pinned thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        name: "General",
    });
    const { openDiscuss } = await start();
    await Promise.all([openDiscuss(channelId), waitForChannels([`discuss.channel_${channelId}`])]);
    await click("[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable", {
        text: "Mitchell Admin",
    });
    await click("button", { text: "Invite to Channel" });
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

QUnit.test("bus subscription kept after receiving a message as non member", async () => {
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
        name: "General",
    });
    const { env, openDiscuss } = await start();
    await Promise.all([openDiscuss(channelId), waitUntilSubscribe(`discuss.channel_${channelId}`)]);
    await pyEnv.withUser(johnUser, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "Hello!" });
    await nextTick();
    await pyEnv.withUser(johnUser, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "Goodbye!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "Goodbye!" });
});
