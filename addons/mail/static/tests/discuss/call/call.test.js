import {
    click,
    contains,
    defineMailModels,
    listenStoreFetch,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
    triggerEvents,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import {
    CROSS_TAB_CLIENT_MESSAGE,
    CROSS_TAB_HOST_MESSAGE,
} from "@mail/discuss/call/common/rtc_service";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, hover, manuallyDispatchProgrammaticEvent, queryFirst } from "@odoo/hoot-dom";
import { mockSendBeacon, mockUserAgent } from "@odoo/hoot-mock";
import {
    asyncStep,
    Command,
    mockService,
    patchWithCleanup,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

import { isMobileOS } from "@web/core/browser/feature_detection";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    mockGetMedia();
});

test("basic rendering", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    await contains(".o-discuss-CallParticipantCard[aria-label='Mitchell Admin']");
    await contains(".o-discuss-CallActionList");
    await contains(".o-discuss-CallMenu-buttonContent");
    await contains(".o-discuss-CallActionList button", { count: 6 });
    await contains("button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    await contains(".o-discuss-CallActionList button[aria-label='Deafen']");
    await contains(".o-discuss-CallActionList button[aria-label='Turn camera on']");
    await contains(".o-discuss-CallActionList button[aria-label='Share Screen']");
    await contains("[title='More']");
    await contains(".o-discuss-CallActionList button[aria-label='Disconnect']");
    await click("[title='More']");
    await contains("[title='Raise Hand']");
    await contains("[title='Fullscreen']");
});

test("mobile UI", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockUserAgent("Chrome/0.0.0 Android (OdooMobile; Linux; Android 13; Odoo TestSuite)");
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    expect(isMobileOS()).toBe(true);
    await contains(".o-discuss-CallActionList button[aria-label='Deafen']");
    await contains("[title='Share Screen']", { count: 0 });
});

test("keep the `more` popover active when hovering it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    await contains(".o-discuss-CallActionList");
    await click("[title='More']");
    const enterFullScreenSelector = ".o-discuss-CallActionList-dropdownItem[title='Fullscreen']";
    await contains(enterFullScreenSelector);
    await hover(queryFirst(enterFullScreenSelector));
    await contains(enterFullScreenSelector);
});

test("no call with odoobot", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: serverState.odoobotId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header");
    await contains("[title='Start Call']", { count: 0 });
});

test("should not display call UI when no more members (self disconnect)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    await click(".o-discuss-CallActionList button[aria-label='Disconnect']");
    await contains(".o-discuss-Call", { count: 0 });
});

test("show call UI in chat window when in call", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "General" });
    await contains(".o-mail-ChatWindow");
    await contains(".o-discuss-Call", { count: 0 });
    await click(".o-mail-ChatWindow-header [title='Start Call']");
    await contains(".o-discuss-Call");
    await contains(".o-mail-ChatWindow-header [title='Start Call']", { count: 0 });
});

test("should disconnect when closing page while in call", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    mockSendBeacon(async (route, data) => {
        if (data instanceof Blob && route === "/mail/rtc/channel/leave_call") {
            const blobText = await data.text();
            const blobData = JSON.parse(blobText);
            asyncStep(`sendBeacon_leave_call:${blobData.params.channel_id}`);
        }
    });

    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    // simulate page close
    await manuallyDispatchProgrammaticEvent(window, "pagehide");
    await waitForSteps([`sendBeacon_leave_call:${channelId}`]);
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
    mockService("mail.sound_effects", {
        play(name) {
            asyncStep(`play - ${name}`);
        },
        stop(name) {
            asyncStep(`stop - ${name}`);
        },
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    // send after init_messaging because bus subscription is done after init_messaging
    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.record/insert",
        new mailDataHelpers.Store(pyEnv["discuss.channel.rtc.session"].browse(sessionId), {
            channel_member_id: { id: memberId },
        })
            .add(pyEnv["discuss.channel.member"].browse(memberId), {
                partner_id: { id: partnerId },
                channel_id: { id: channelId, model: "discuss.channel" },
                rtc_inviting_session_id: { id: sessionId },
            })
            .get_result()
    );
    await contains(".o-discuss-CallInvitation");
    await waitForSteps(["play - call-invitation"]);
    // Simulate stop receiving call invitation

    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.record/insert",
        new mailDataHelpers.Store(pyEnv["discuss.channel.member"].browse(memberId), {
            rtc_inviting_session_id: false,
        }).get_result()
    );
    await contains(".o-discuss-CallInvitation", { count: 0 });
    await waitForSteps(["stop - call-invitation"]);
});

test("can share screen", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await contains("video");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='More']");
    await click("[title='Stop Sharing Screen']");
    await contains("video", { count: 0 });
});

test("can share user camera", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='Turn camera on']");
    await contains("video");
    await click("[title='Stop camera']");
    await contains("video", { count: 0 });
});

test("Camera video stream stays in focus when on/off", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click(".o-discuss-CallParticipantCard-avatar");
    await click("[title='Turn camera on']");
    await click("[title='Stop camera']");
    await click("[title='Turn camera on']");
    await contains("video[type='camera']:not(.o-inset)");
    // test screen sharing then camera on to check camera aside
    await click("[title='Stop camera']");
    await click("[title='Share Screen']");
    await click("[title='Turn camera on']");
    await contains("video[type='screen']:not(.o-inset)");
    await contains("video[type='camera'].o-inset");
});

test("Create a direct message channel when clicking on start a meeting", async () => {
    await start();
    await openDiscuss();
    await click("button[title='New Meeting']");
    await contains(".o-mail-DiscussSidebarChannel", { text: "Mitchell Admin" });
    await contains(".o-discuss-Call");
    await contains(".o-discuss-ChannelInvitation");
});

test("Can share user camera and screen together", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await click("[title='Turn camera on']");
    await contains("video", { count: 2 });
});

test("Click on inset card should replace the inset and active stream together", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await click("[title='Turn camera on']");
    await contains("video[type='screen']:not(.o-inset)");
    await click("video[type='camera'].o-inset");
    await contains("video[type='screen'].o-inset");
    await contains("video[type='camera']:not(.o-inset)");
});

test("join/leave sounds are only played on main tab", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    patchWithCleanup(env1.services["mail.sound_effects"], {
        play(name) {
            asyncStep(`tab1 - play - ${name}`);
        },
    });
    patchWithCleanup(env2.services["mail.sound_effects"], {
        play(name) {
            asyncStep(`tab2 - play - ${name}`);
        },
    });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await click("[title='Start Call']", { target: env1 });
    await contains(".o-discuss-Call", { target: env1 });
    await contains(".o-discuss-Call", { target: env2 });
    await waitForSteps(["tab1 - play - call-join"]);
    await click("[title='Disconnect']:not([disabled])", { target: env1 });
    await contains(".o-discuss-Call", { target: env1, count: 0 });
    await contains(".o-discuss-Call", { target: env2, count: 0 });
    await waitForSteps(["tab1 - play - call-leave"]);
});

test("'New Meeting' in mobile", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 2" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({ name: "Slytherin" });
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Notifications" });
    await click("button", { text: "Chats" });
    await click("button[title='New Meeting']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Partner 2" });
    await click("button:not([disabled])", { text: "Invite to Group Chat" });
    await contains(".o-discuss-Call");
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Members" });
    await contains(".o-discuss-ChannelMember", { text: "Partner 2" });
});

test("Systray icon shows latest action", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-CallMenu-buttonContent .fa-microphone");
    await click("[title='Mute (shift+m)']");
    await contains(".o-discuss-CallMenu-buttonContent .fa-microphone-slash");
    await click("[title='Deafen (shift+d)']");
    await contains(".o-discuss-CallMenu-buttonContent .fa-deaf");
    await click("[title='Turn camera on']");
    await contains(".o-discuss-CallMenu-buttonContent .fa-video-camera");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await contains(".o-discuss-CallMenu-buttonContent .fa-desktop");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='More']");
    await click("[title='Raise Hand']");
    await contains(".o-discuss-CallMenu-buttonContent .fa-hand-paper-o");
});

test("Systray icon keeps track of earlier actions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-CallMenu-buttonContent .fa-microphone");
    await click("[title='More']");
    await click("[title='Share Screen']");
    // stack: ["share-screen"]
    await contains(".o-discuss-CallMenu-buttonContent .fa-desktop");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='Turn camera on']");
    // stack: ["video", "share-screen"]
    await contains(".o-discuss-CallMenu-buttonContent .fa-video-camera");
    await click("[title='Mute (shift+m)']");
    // stack: ["mute", "video", "share-screen"]
    await contains(".o-discuss-CallMenu-buttonContent .fa-microphone-slash");
    await click("[title='Unmute (shift+m)']");
    // stack: ["video", "share-screen"]
    await contains(".o-discuss-CallMenu-buttonContent .fa-video-camera");
    await click("[title='Stop camera']");
    // stack: ["share-screen"]
    await contains(".o-discuss-CallMenu-buttonContent .fa-desktop");
});

test("show call participants in discuss sidebar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-mail-DiscussSidebar", {
        contains: [
            ".o-mail-DiscussSidebarChannel:contains('General') ~ .o-mail-DiscussSidebarCallParticipants:contains(Mitchell Admin)",
        ],
    });
});

test("Sort call participants in side bar by name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["discuss.channel.rtc.session"].create([
        {
            channel_member_id: pyEnv["discuss.channel.member"].create({
                channel_id: channelId,
                partner_id: pyEnv["res.partner"].create({ name: "CCC" }),
            }),
            channel_id: channelId,
        },
        {
            channel_member_id: pyEnv["discuss.channel.member"].create({
                channel_id: channelId,
                partner_id: pyEnv["res.partner"].create({ name: "AAA" }),
            }),
            channel_id: channelId,
        },
        {
            channel_member_id: pyEnv["discuss.channel.member"].create({
                channel_id: channelId,
                partner_id: pyEnv["res.partner"].create({ name: "BBB" }),
            }),
            channel_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await click("[title='Expand participants']");
    await contains(".o-mail-DiscussSidebarCallParticipants", {
        contains: [
            ".o-mail-DiscussSidebarCallParticipants-participant:nth-child(1):contains('AAA')",
        ],
    });
    await contains(" .o-mail-DiscussSidebarCallParticipants", {
        contains: [
            ".o-mail-DiscussSidebarCallParticipants-participant:nth-child(2):contains('BBB')",
        ],
    });
    await contains(" .o-mail-DiscussSidebarCallParticipants", {
        contains: [
            ".o-mail-DiscussSidebarCallParticipants-participant:nth-child(3):contains('CCC')",
        ],
    });
});

test("expand call participants when joining a call", async () => {
    const pyEnv = await startServer();
    const partners = pyEnv["res.partner"].create([
        { name: "Alice" },
        { name: "Bob" },
        { name: "Cathy" },
        { name: "David" },
        { name: "Eric" },
        { name: "Frank" },
        { name: "Grace" },
        { name: "Henry" },
        { name: "Ivy" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (const partner of partners) {
        const memberId = pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: partner,
        });
        pyEnv["discuss.channel.rtc.session"].create({
            channel_member_id: memberId,
            channel_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarCallParticipants img", { count: 7 });
    await contains("img[title='Alice']");
    await contains("img[title='Bob']");
    await contains("img[title='Cathy']");
    await contains("img[title='David']");
    await contains(".o-mail-DiscussSidebarCallParticipants span", { text: "+2" });
    await click("[title='Join Call']");
    await contains(".o-mail-DiscussSidebarCallParticipants img", { count: 10 });
    await contains("img[title='Alice']");
    await contains("img[title='Bob']");
    await contains("img[title='Cathy']");
    await contains("img[title='David']");
    await contains("img[title='Eric']");
    await contains("img[title='Frank']");
    await contains("img[title='Mitchell Admin']");
});

test("start call when accepting from push notification", async () => {
    const serviceWorker = Object.assign(new EventTarget(), {
        register: () => Promise.resolve(),
        ready: Promise.resolve(),
    });
    patchWithCleanup(window.navigator, { serviceWorker });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussContent-threadName[title=Inbox]");
    serviceWorker.dispatchEvent(
        new MessageEvent("message", {
            data: { action: "OPEN_CHANNEL", data: { id: channelId, joinCall: true } },
        })
    );
    await contains(".o-mail-DiscussContent-threadName[title=General]");
    await contains(`.o-discuss-CallParticipantCard[title='${serverState.partnerName}']`);
});

test("Use saved volume settings", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerName = "Another Participant";
    const partnerId = pyEnv["res.partner"].create({ name: partnerName });
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: partnerId,
        }),
        channel_id: channelId,
    });
    const expectedVolume = 0.31;
    pyEnv["res.users.settings.volumes"].create({
        user_setting_id: pyEnv["res.users.settings"].create({
            user_id: serverState.userId,
        }),
        partner_id: partnerId,
        volume: expectedVolume,
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Join the Call']");
    await contains(".o-discuss-Call");
    await triggerEvents(`.o-discuss-CallParticipantCard[title='${partnerName}']`, ["mouseenter"]);
    await click("button[title='Participant options']");
    await contains(".o-discuss-CallContextMenu");
    const rangeInput = queryFirst(".o-discuss-CallContextMenu input[type='range']");
    expect(rangeInput.value).toBe(expectedVolume.toString());
    rangeInput.dispatchEvent(new Event("change")); // to trigger the volume change
    await click(".o-discuss-CallActionList button[aria-label='Disconnect']");
});

test("show call participants after stopping screen share", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='Share Screen']");
    await contains("video");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='Stop Sharing Screen']");
    await contains("video", { count: 0 });
    // when all participant cards are shown they are minimized
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard .o-minimized");
});

test("show call participants after stopping camera share", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='Turn camera on']");
    await contains("video");
    await click("[title='Stop camera']");
    await contains("video", { count: 0 });
    // when all participant cards are shown they are minimized
    await contains(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard .o-minimized");
});

test("Cross tab calls: tabs can interact with calls remotely", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const broadcastChannel = new BroadcastChannel("call_sync_state");
    const sessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "remoteHost" }),
        }),
        channel_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    expect("[title='Disconnect']").not.toHaveCount();
    expect("[title='Mute (shift+m)']").not.toHaveCount();
    expect("[title='Deafen (shift+d)']").not.toHaveCount();
    broadcastChannel.postMessage({
        type: CROSS_TAB_HOST_MESSAGE.UPDATE_REMOTE,
        hostedChannelId: channelId,
        hostedSessionId: sessionId,
        changes: {
            [sessionId]: {
                is_muted: false,
                is_deaf: false,
            },
        },
    });
    await contains("[title='Disconnect']");
    await contains("[title='Deafen (shift+d)']");

    broadcastChannel.onmessage = (event) => {
        if (event.data.type === CROSS_TAB_CLIENT_MESSAGE.REQUEST_ACTION) {
            asyncStep(`is_muted:${event.data.changes["is_muted"]}`);
        }
    };
    await click("[title='Mute (shift+m)']");
    await waitForSteps(["is_muted:true"]);
});

test("automatically cancel incoming call after some time", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const [memberId] = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    const rtcSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: memberId,
        channel_id: channelId,
    });
    pyEnv["discuss.channel.member"].write([memberId], { rtc_inviting_session_id: rtcSessionId });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-CallInvitation");
    await advanceTime(30_000);
    await contains(".o-discuss-CallInvitation", { count: 0 });
});

test("should also invite to the call when inviting to the channel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    await click(".o-mail-DiscussContent-header button[title='Invite People']");
    await contains(".o-discuss-ChannelInvitation");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "TestPartner" });
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await contains(".o-discuss-CallParticipantCard.o-isInvitation");
});

test("can join / leave call from discuss sidebar actions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Start Call')");
    await contains(".o-discuss-Call");
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Disconnect')");
    await contains(".o-discuss-Call", { count: 0 });
});

test("shows warning on infinite mirror effect (screen-sharing then fullscreen)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='More']");
    await click("[title='Share Screen']");
    await contains("video");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='More']");
    await click("[title='Fullscreen']");
    await contains(".o-discuss-CallInfiniteMirroringWarning");
    await contains(
        ".o-discuss-CallInfiniteMirroringWarning:contains('To avoid the infinite mirror effect, please share a specific window or tab or another monitor.')"
    );
    await contains("button:contains('Stream paused') i.fa-pause-circle-o");
    await hover(queryFirst("button:contains('Stream paused')"));
    await contains("button:contains('Resume stream') i.fa-play-circle-o");
});
