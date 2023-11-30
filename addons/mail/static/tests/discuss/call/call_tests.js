/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";
import {
    afterNextRender,
    click,
    mockGetMedia,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import { browser } from "@web/core/browser/browser";
import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click as clickContains, contains } from "@web/../tests/utils";

QUnit.module("call");

QUnit.test("basic rendering", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-discuss-Call");
    assert.containsOnce($, ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin']");
    assert.containsOnce($, ".o-discuss-CallActionList");
    assert.containsOnce($, ".o-discuss-CallMenu-buttonContent");
    assert.containsN($, ".o-discuss-CallActionList button", 5);
    assert.containsOnce($, "button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    assert.containsOnce($, ".o-discuss-CallActionList button[aria-label='Deafen']");
    assert.containsOnce($, ".o-discuss-CallActionList button[aria-label='Turn camera on']");
    assert.containsOnce($, "button[title='More']");
    assert.containsOnce($, ".o-discuss-CallActionList button[aria-label='Disconnect']");
    await click("button[title='More']");
    assert.containsOnce($, "[title='Raise Hand']");
    assert.containsOnce($, "[title='Share Screen']");
    assert.containsOnce($, "[title='Enter Full Screen']");
});

QUnit.test("no call with odoobot", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: pyEnv.odoobotId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Discuss-header button[title='Start a Call']");
});

QUnit.test("should not display call UI when no more members (self disconnect)", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-discuss-Call");

    click(".o-discuss-CallActionList button[aria-label='Disconnect']");
    await waitUntil(".o-discuss-Call", 0);
});

QUnit.test("show call UI in chat window when in call", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:contains(General)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsNone($, ".o-discuss-Call");
    assert.containsOnce(
        $,
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Start a Call']"
    );

    await click(".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Start a Call']");
    assert.containsOnce($, ".o-discuss-Call");
    assert.containsNone(
        $,
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Start a Call']"
    );
});

QUnit.test("should disconnect when closing page while in call", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
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

    await click(".o-mail-Discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-discuss-Call");
    // simulate page close
    await afterNextRender(() => window.dispatchEvent(new Event("pagehide"), { bubble: true }));
    await nextTick();
    assert.verifySteps(["sendBeacon_leave_call"]);
});

QUnit.test("should display invitations", async (assert) => {
    patchWithCleanup(
        browser,
        {
            Audio: class extends Audio {
                pause() {
                    assert.step("pause_sound_effect");
                }
                play() {
                    assert.step("play_sound_effect");
                }
            },
        },
        { pure: true }
    );
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
    await start();
    // Simulate receive call invitation
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            Thread: {
                id: channelId,
                model: "discuss.channel",
                rtcInvitingSession: { id: sessionId, channelMember: { id: memberId } },
            },
        });
    });
    assert.containsOnce($, ".o-discuss-CallInvitation");
    assert.verifySteps(["play_sound_effect"]);
    // Simulate stop receiving call invitation
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            Thread: {
                id: channelId,
                model: "discuss.channel",
                rtcInvitingSession: [["unlink"]],
            },
        });
    });
    assert.containsNone($, ".o-discuss-CallInvitation");
    assert.verifySteps(["pause_sound_effect"]);
});

QUnit.test("can share screen", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Start a Call']");
    await click(".o-discuss-CallActionList [title='More']");
    await click("[title='Share Screen']");
    assert.containsOnce($, ".o-discuss-CallParticipantCard video");
    await click(".o-discuss-CallActionList [title='More']");
    await click("[title='Stop Sharing Screen']");
    assert.containsNone($, ".o-discuss-CallParticipantCard video");
});

QUnit.test("can share user camera", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Start a Call']");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    assert.containsOnce($, ".o-discuss-CallParticipantCard video");
    await click(".o-discuss-CallActionList button[title='Stop camera']");
    assert.containsNone($, ".o-discuss-CallParticipantCard video");
});

QUnit.test("Create a direct message channel when clicking on start a meeting", async (assert) => {
    mockGetMedia();
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Start a meeting)");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Mitchell Admin)");
    assert.containsOnce($, ".o-discuss-Call");
});

QUnit.test("join/leave sounds are only played on main tab", async (assert) => {
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
    await clickContains("[title='Start a Call']", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab2.target });
    assert.verifySteps(["tab1 - play - channel-join"]);
    await clickContains("[title='Disconnect']:not([disabled])", { target: tab1.target });
    await contains(".o-discuss-Call", { target: tab1.target, count: 0 });
    await contains(".o-discuss-Call", { target: tab2.target, count: 0 });
    assert.verifySteps(["tab1 - play - channel-leave"]);
});
