/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { mockGetMedia, start } from "@mail/../tests/helpers/test_utils";

import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, triggerEvents } from "@web/../tests/utils";

QUnit.module("call");

QUnit.test("basic rendering", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Start a Call']");
    await contains(".o-discuss-Call");
    await contains(".o-discuss-CallParticipantCard[aria-label='Mitchell Admin']");
    await contains(".o-discuss-CallActionList");
    await contains(".o-discuss-CallMenu-buttonContent");
    await contains(".o-discuss-CallActionList button", { count: 5 });
    await contains("button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    await contains(".o-discuss-CallActionList button[aria-label='Deafen']");
    await contains(".o-discuss-CallActionList button[aria-label='Turn camera on']");
    await contains("[title='More']");
    await contains(".o-discuss-CallActionList button[aria-label='Disconnect']");
    await click("[title='More']");
    await contains("[title='Raise Hand']");
    await contains("[title='Share Screen']");
    await contains("[title='Enter Full Screen']");
});

QUnit.test("no call with odoobot", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: pyEnv.odoobotId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Discuss-header");
    await contains("[title='Start a Call']", { count: 0 });
});

QUnit.test("should not display call UI when no more members (self disconnect)", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Start a Call']");
    await contains(".o-discuss-Call");
    await click(".o-discuss-CallActionList button[aria-label='Disconnect']");
    await contains(".o-discuss-Call", { count: 0 });
});

QUnit.test("show call UI in chat window when in call", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "General" });
    await contains(".o-mail-ChatWindow");
    await contains(".o-discuss-Call", { count: 0 });
    await click(".o-mail-ChatWindow-command[title='Start a Call']");
    await contains(".o-discuss-Call");
    await contains(".o-mail-ChatWindow-command[title='Start a Call']", { count: 0 });
});

QUnit.test("should disconnect when closing page while in call", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            sendBeacon: async (route, data) => {
                if (data instanceof Blob && route === "/mail/rtc/channel/leave_call") {
                    assert.step("sendBeacon_leave_call");
                    const blobText = await data.text();
                    const blobData = JSON.parse(blobText);
                    assert.strictEqual(blobData.params.channel_id, channelId);
                }
            },
        },
    });

    await click("[title='Start a Call']");
    await contains(".o-discuss-Call");
    // simulate page close
    window.dispatchEvent(new Event("pagehide"), { bubble: true });
    assert.verifySteps(["sendBeacon_leave_call"]);
});

QUnit.test("should display invitations", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId = pyEnv["res.partner"].create({ name: "InvitationSender" });
    const memberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: partnerId,
    });
    const sessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: memberId,
        channel_id: channelId,
    });
    const { env } = await start();
    patchWithCleanup(env.services["mail.sound_effects"], {
        play(name) {
            assert.step(`play - ${name}`);
            super.play(...arguments);
        },
        stop(name) {
            assert.step(`stop - ${name}`);
            super.stop(...arguments);
        },
    });
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
        Thread: {
            id: channelId,
            model: "discuss.channel",
            rtcInvitingSession: { id: sessionId, channelMember: { id: memberId } },
        },
    });
    await contains(".o-discuss-CallInvitation");
    assert.verifySteps(["play - incoming-call"]);
    // Simulate stop receiving call invitation
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
        Thread: {
            id: channelId,
            model: "discuss.channel",
            rtcInvitingSession: false,
        },
    });
    await contains(".o-discuss-CallInvitation", { count: 0 });
    assert.verifySteps(["stop - incoming-call"]);
});

QUnit.test("can share screen", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await contains("video");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='More']");
    await click("[title='Stop Sharing Screen']");
    await contains("video", { count: 0 });
});

QUnit.test("can share user camera", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='Turn camera on']");
    await contains("video");
    await click("[title='Stop camera']");
    await contains("video", { count: 0 });
});

QUnit.test("Create a direct message channel when clicking on start a meeting", async () => {
    mockGetMedia();
    const { openDiscuss } = await start();
    openDiscuss();
    await click("button", { text: "Start a meeting" });
    await contains(".o-mail-DiscussSidebarChannel", { text: "Mitchell Admin" });
    await contains(".o-discuss-Call");
    await contains(".o-discuss-ChannelInvitation");
});

QUnit.test("Can share user camera and screen together", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await click("[title='Turn camera on']");
    await contains("video", { count: 2 });
});

QUnit.test("Click on inset card should replace the inset and active stream together", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await click("[title='Turn camera on']");
    await contains("video[type='screen']:not(.o-inset)");
    await click("video[type='camera'].o-inset");
    await contains("video[type='screen'].o-inset");
    await contains("video[type='camera']:not(.o-inset)");
});

QUnit.test("join/leave sounds are only played on main tab", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    patchWithCleanup(tab1.env.services["mail.sound_effects"], {
        play(name) {
            assert.step(`tab1 - play - ${name}`);
        },
    });
    patchWithCleanup(tab2.env.services["mail.sound_effects"], {
        play(name) {
            assert.step(`tab2 - play - ${name}`);
        },
    });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    await click("[title='Start a Call']", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab2.target });
    assert.verifySteps(["tab1 - play - channel-join"]);
    await click("[title='Disconnect']:not([disabled])", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab1.target, count: 0 });
    await contains(".o-discuss-Call", { target: tab2.target, count: 0 });
    assert.verifySteps(["tab1 - play - channel-leave"]);
});
