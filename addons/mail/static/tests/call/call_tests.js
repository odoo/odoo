/** @odoo-module **/

import {
    afterNextRender,
    click,
    start,
    startServer,
    mockGetMedia,
} from "@mail/../tests/helpers/test_utils";
import { editInput, nextTick, patchWithCleanup, triggerEvent } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { Command } from "../helpers/command";
import { DEBOUNCE_FETCH_SUGGESTION_TIME } from "@mail/discuss_app/channel_selector";

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
    assert.containsOnce($, ".o-mail-Call");
    assert.containsOnce($, ".o-mail-CallParticipantCard[aria-label='Mitchell Admin']");
    assert.containsOnce($, ".o-mail-CallActionList");
    assert.containsOnce($, ".o-mail-CallMenu-buttonContent");
    assert.containsN($, ".o-mail-CallActionList button", 7);
    assert.containsOnce($, "button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    assert.containsOnce($, ".o-mail-CallActionList button[aria-label='Deafen']");
    assert.containsOnce($, ".o-mail-CallActionList button[aria-label='Raise hand']");
    assert.containsOnce($, ".o-mail-CallActionList button[aria-label='Turn camera on']");
    assert.containsOnce($, ".o-mail-CallActionList button[aria-label='Share screen']");
    assert.containsOnce($, ".o-mail-CallActionList button[aria-label='Enter Full Screen']");
    assert.containsOnce($, ".o-mail-CallActionList button[aria-label='Disconnect']");
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
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Start a Call']");
    assert.containsOnce($, ".o-mail-Call");

    await click(".o-mail-CallActionList button[aria-label='Disconnect']");
    assert.containsNone($, ".o-mail-Call");
});

QUnit.test("show call UI in chat window when in call", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem:contains(General)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsNone($, ".o-mail-Call");
    assert.containsOnce(
        $,
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Start a Call']"
    );

    await click(".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Start a Call']");
    assert.containsOnce($, ".o-mail-Call");
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
    assert.containsOnce($, ".o-mail-Call");
    // simulate page close
    await afterNextRender(() => window.dispatchEvent(new Event("pagehide"), { bubble: true }));
    await nextTick();
    assert.verifySteps(["sendBeacon_leave_call"]);
});

QUnit.test("no default rtc after joining a chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");

    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(document.body, ".o-mail-ChannelSelector input", "mario"));
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await click(".o-mail-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-mail-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Discuss-content .o-mail-Message");
    assert.containsNone($, ".o-mail-Call");
});

QUnit.test("no default rtc after joining a group conversation", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(document.body, ".o-mail-ChannelSelector input", "mario"));
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await click(".o-mail-ChannelSelector-suggestion");
    await afterNextRender(() => editInput(document.body, ".o-mail-ChannelSelector input", "luigi"));
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await click(".o-mail-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-mail-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Discuss-content .o-mail-Message");
    assert.containsNone($, ".o-mail-Call");
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
    assert.containsOnce($, ".o-mail-CallInvitation");
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
    assert.containsNone($, ".o-mail-CallInvitation");
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
    await click(".o-mail-CallActionList button[title='Share screen']");
    assert.containsOnce($, ".o-mail-CallParticipantCard video");
    await click(".o-mail-CallActionList button[title='Stop screen sharing']");
    assert.containsNone($, ".o-mail-CallParticipantCard video");
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
    await click(".o-mail-CallActionList button[title='Turn camera on']");
    assert.containsOnce($, ".o-mail-CallParticipantCard video");
    await click(".o-mail-CallActionList button[title='Stop camera']");
    assert.containsNone($, ".o-mail-CallParticipantCard video");
});
