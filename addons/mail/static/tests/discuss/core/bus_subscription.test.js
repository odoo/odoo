import { waitForChannels } from "@bus/../tests/bus_test_helpers";
import { onWebsocketEvent } from "@bus/../tests/mock_websocket";
import { WebsocketWorker } from "@bus/workers/websocket_worker";

import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, edit, expect, mockDate, press, runAllTimers, test } from "@odoo/hoot";

import { Command, patchWithCleanup } from "@web/../tests/web_test_helpers";

defineMailModels();

describe.current.tags("desktop");

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
    await click(".o-dropdown-item:text(Hide)");
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test("bus subscription updated when opening/closing chat window as a non member", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        name: "Sales",
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow:has(:text('Sales'))");
    await waitForChannels([`discuss.channel_${channelId}`]);
    await click("[title*='Close Chat Window']", {
        parent: [".o-mail-ChatWindow:has(:text('Sales'))"],
    });
    await contains(".o-mail-ChatWindow:has(:text('Sales'))", { count: 0 });
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
    await press(["control", "k"]);
    await click(".o_command_palette_search input");
    await edit("@");
    await click(".o-mail-DiscussCommand:text('Sales')");
    await waitForChannels([`discuss.channel_${channelId}`]);
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Mitchell Admin'))");
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test("bus subscription is refreshed when channel is joined", async () => {
    patchWithCleanup(WebsocketWorker, { OUTGOING_BATCH_DELAY: 10 });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await openDiscuss();
    await runAllTimers(); // settle the bus subscriptions from start/openDiscuss
    onWebsocketEvent("subscribe", () => expect.step("subscribe"));
    await click("input[placeholder='Search']");
    await insertText(
        ".o_command_palette_search input[placeholder='Search conversations']",
        "new channel"
    );
    await expect.waitForSteps(["subscribe"]);
});

test("bus subscription is refreshed when channel is left", async () => {
    patchWithCleanup(WebsocketWorker, { OUTGOING_BATCH_DELAY: 10 });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await openDiscuss();
    await runAllTimers(); // settle the bus subscriptions from start/openDiscuss
    onWebsocketEvent("subscribe", () => expect.step("subscribe"));
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await expect.waitForSteps(["subscribe"]);
});
