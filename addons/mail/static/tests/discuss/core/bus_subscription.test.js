import { waitForChannels } from "@bus/../tests/bus_test_helpers";
import { onWebsocketEvent } from "@bus/../tests/mock_websocket";

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

import { describe, edit, expect, mockDate, press, test } from "@odoo/hoot";

import { Command } from "@web/../tests/web_test_helpers";

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
    await click(".o-dropdown-item:contains('Leave Channel')");
    await click("button", { text: "Leave Conversation" });
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
    await contains(".o-mail-ChatWindow", { text: "Sales" });
    await waitForChannels([`discuss.channel_${channelId}`]);
    await click("[title*='Close Chat Window']", {
        parent: [".o-mail-ChatWindow", { text: "Sales" }],
    });
    await contains(".o-mail-ChatWindow", { count: 0, text: "Sales" });
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
    await press(["control", "k"]);
    await click(".o_command_palette_search input");
    await edit("@");
    await click(".o-mail-DiscussCommand", { text: "Sales" });
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
    await click("[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", {
        text: "Mitchell Admin",
    });
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test("bus subscription is refreshed when channel is joined", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    onWebsocketEvent("subscribe", () => expect.step("subscribe"));
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await expect.waitForSteps(["subscribe"]);
    await openDiscuss();
    await expect.waitForSteps([]);
    await click("input[placeholder='Search conversations']");
    await insertText("input[placeholder='Search a conversation']", "new channel");
    await expect.waitForSteps(["subscribe"]);
});

test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    onWebsocketEvent("subscribe", () => expect.step("subscribe"));
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await expect.waitForSteps(["subscribe"]);
    await openDiscuss();
    await expect.waitForSteps([]);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await expect.waitForSteps(["subscribe"]);
});
