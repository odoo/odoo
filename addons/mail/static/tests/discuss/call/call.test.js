/** @odoo-module alias=@mail/../tests/discuss/call/call_tests default=false */
const test = QUnit.test; // QUnit.test()

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { SIZES, patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { mockGetMedia, openDiscuss, start } from "@mail/../tests/helpers/test_utils";

import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, step, triggerEvents } from "@web/../tests/utils";

QUnit.module("call");

test("basic rendering", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
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

test("no call with odoobot", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: pyEnv.odoobotId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-header");
    await contains("[title='Start a Call']", { count: 0 });
});

test("should not display call UI when no more members (self disconnect)", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start a Call']");
    await contains(".o-discuss-Call");
    await click(".o-discuss-CallActionList button[aria-label='Disconnect']");
    await contains(".o-discuss-Call", { count: 0 });
});

test("show call UI in chat window when in call", async () => {
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

test("should disconnect when closing page while in call", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            sendBeacon: async (route, data) => {
                if (data instanceof Blob && route === "/mail/rtc/channel/leave_call") {
                    const blobText = await data.text();
                    const blobData = JSON.parse(blobText);
                    step(`sendBeacon_leave_call:${blobData.params.channel_id}`);
                }
            },
        },
    });

    await click("[title='Start a Call']");
    await contains(".o-discuss-Call");
    // simulate page close
    window.dispatchEvent(new Event("pagehide"), { bubble: true });
    await assertSteps([`sendBeacon_leave_call:${channelId}`]);
});

test("should display invitations", async () => {
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
    const { env } = await start({
        async mockRPC(route, args, originalRpc) {
            if (route === "/mail/action" && args.init_messaging) {
                const res = await originalRpc(...arguments);
                step(`/mail/action - ${JSON.stringify(args)}`);
                return res;
            }
        },
    });
    patchWithCleanup(env.services["mail.sound_effects"], {
        play(name) {
            step(`play - ${name}`);
            super.play(...arguments);
        },
        stop(name) {
            step(`stop - ${name}`);
            super.stop(...arguments);
        },
    });
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
        Thread: {
            id: channelId,
            model: "discuss.channel",
            rtcInvitingSession: {
                id: sessionId,
                channelMember: {
                    id: memberId,
                    channel_id: channelId,
                    persona: {
                        id: partnerId,
                        type: "partner",
                    },
                },
            },
        },
    });
    await contains(".o-discuss-CallInvitation");
    await assertSteps(["play - incoming-call"]);
    // Simulate stop receiving call invitation
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
        Thread: {
            id: channelId,
            model: "discuss.channel",
            rtcInvitingSession: false,
        },
    });
    await contains(".o-discuss-CallInvitation", { count: 0 });
    await assertSteps(["stop - incoming-call"]);
});

test("can share screen", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await contains("video");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='More']");
    await click("[title='Stop Sharing Screen']");
    await contains("video", { count: 0 });
});

test("can share user camera", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='Turn camera on']");
    await contains("video");
    await click("[title='Stop camera']");
    await contains("video", { count: 0 });
});

test("Create a direct message channel when clicking on start a meeting", async () => {
    mockGetMedia();
    await start();
    await openDiscuss();
    await click("button", { text: "Start a meeting" });
    await contains(".o-mail-DiscussSidebarChannel", { text: "Mitchell Admin" });
    await contains(".o-discuss-Call");
    await contains(".o-discuss-ChannelInvitation");
});

test("Can share user camera and screen together", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await click("[title='Turn camera on']");
    await contains("video", { count: 2 });
});

test("Click on inset card should replace the inset and active stream together", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start a Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await click("[title='Turn camera on']");
    await contains("video[type='screen']:not(.o-inset)");
    await click("video[type='camera'].o-inset");
    await contains("video[type='screen'].o-inset");
    await contains("video[type='camera']:not(.o-inset)");
});

test("join/leave sounds are only played on main tab", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    patchWithCleanup(tab1.env.services["mail.sound_effects"], {
        play(name) {
            step(`tab1 - play - ${name}`);
        },
    });
    patchWithCleanup(tab2.env.services["mail.sound_effects"], {
        play(name) {
            step(`tab2 - play - ${name}`);
        },
    });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    await click("[title='Start a Call']", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab2.target });
    await assertSteps(["tab1 - play - channel-join"]);
    await click("[title='Disconnect']:not([disabled])", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab1.target, count: 0 });
    await contains(".o-discuss-Call", { target: tab2.target, count: 0 });
    await assertSteps(["tab1 - play - channel-leave"]);
});

test("'Start a meeting' in mobile", async () => {
    mockGetMedia();
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 2" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({ name: "Slytherin" });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Inbox" });
    await click("button", { text: "Chat" });
    await click("button", { text: "Start a meeting" });
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Partner 2" });
    await click("button:not([disabled])", { text: "Invite to Group Chat" });
    await contains(".o-discuss-Call");
    await click("[title='Open Actions Menu']");
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "Partner 2" });
});
