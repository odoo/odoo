import {
    click,
    contains as mailContains,
    createVideoStream,
    defineMailModels,
    dragenterFiles,
    dropFiles,
    insertText,
    listenStoreFetch,
    makeMockRtcNetwork,
    mockBrowserFullscreen,
    mockGetMedia,
    mockPermissionsPrompt,
    mockPipWindow,
    onRpcAfter,
    openDiscuss,
    openMessagingMenu,
    patchUiSize,
    setupChatHub,
    SIZES,
    start,
    startServer,
    triggerEvents,
    triggerHotkey,
    waitStoreFetch,
    MENU_ACTIVE_IDS,
    hover,
} from "@mail/../tests/mail_test_helpers";
import { Store } from "@mail/../tests/mock_server/store";
import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";
import {
    CROSS_TAB_CLIENT_MESSAGE,
    CROSS_TAB_HOST_MESSAGE,
    Rtc,
} from "@mail/discuss/call/common/rtc_service";
import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { Meeting } from "@mail/discuss/call/common/meeting";
import { POLL_CLOSE_WINDOW_TIMEOUT } from "@mail/core/common/mail_popout_service";

import {
    advanceTime,
    beforeEach,
    describe,
    expect,
    manuallyDispatchProgrammaticEvent,
    mockDate,
    mockSendBeacon,
    mockUserAgent,
    queryFirst,
    test,
} from "@odoo/hoot";
import { press, waitFor, waitForNone, waitUntil } from "@odoo/hoot-dom";
import {
    Command,
    contains,
    getService,
    mockService,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

import { waitNotifications } from "@bus/../tests/bus_test_helpers";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

describe.current.tags("desktop");
defineMailModels();

let streams = [];
beforeEach(() => {
    streams = mockGetMedia();
});

test("basic rendering", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Mitchell Admin']:count(1)");
    await waitFor(".o-discuss-CallActionList:count(1)");
    await waitFor(".o-discuss-CallMenu-buttonContent:count(1)");
    await waitFor(".o-discuss-CallActionList button:count(8)");
    await mailContains("button[aria-label='Unmute'], button[aria-label='Mute']"); // FIXME depends on current browser permission
    await waitFor("button[aria-label='Voice Settings']:count(1)");
    // Self's talking bars stand in for the chevrons of the voice settings and the call menu.
    await waitFor(
        "button[aria-label='Voice Settings'] .o-discuss-TalkingAudioBars:not(.o-isTalking):count(1)"
    );
    await waitFor(
        ".o-discuss-CallMenu-actionsAudioBars .o-discuss-TalkingAudioBars:not(.o-isTalking):count(1)"
    );
    Object.assign(getService("discuss.rtc").selfSession, { is_muted: false, isTalking: true });
    await waitFor(
        "button[aria-label='Voice Settings'] .o-discuss-TalkingAudioBars.o-isTalking:count(1)"
    );
    await waitFor(
        ".o-discuss-CallMenu-actionsAudioBars .o-discuss-TalkingAudioBars.o-isTalking:count(1)"
    );
    await waitFor(".o-discuss-CallActionList button[aria-label='Turn camera on']:count(1)");
    await waitFor("button[aria-label='Video Settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[aria-label='Share Screen']:count(1)");
    await waitFor("button[aria-label='Raise Hand']:count(1)");
    await waitFor(".o-discuss-CallActionList button[aria-label='Disconnect']:count(1)");
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await waitFor("[name='fullscreen']:count(1)");
    await waitFor("[name='change-layout']:count(1)");
    await waitFor("[name='picture-in-picture']:count(1)");
});

test("show the recording indicator to all and the stop control to recorders", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    rtc.recordingState = {
        audio: true,
        transcription: false,
        video: false,
    };
    await waitFor(".o-discuss-CallRecordingIndicator:count(1)");
    await hover(".o-discuss-CallRecordingIndicator");
    await waitForNone(".o-discuss-CallRecordingIndicator button:text('Stop recording')");
    rtc.can_record_audio = true;
    await waitFor(".o-discuss-CallRecordingIndicator button:text('Stop recording'):count(1)");
    patch(rtc, {
        setRecording(options) {
            expect(options).toEqual({ audio: false, transcription: false, video: false });
            expect.step("stop recording");
        },
    });
    await contains(
        ".o-discuss-CallRecordingIndicator button:text('Stop recording'):count(1)"
    ).click();
    expect.verifySteps(["stop recording"]);
});

test("recording is in the extended action menu", async () => {
    await startCallWithRecordingPermissions();
    await waitForNone(".o-discuss-CallActionList [name='record-call']");
    await contains(".o-discuss-CallActionList [name='more-action:call-layout']:count(1)").click();
    await contains(".o-dropdown-item[name='record-call']:count(1)").click();
    await waitFor(".o-discuss-RecordingDialog:count(1)");
});

test("recording state echoes do not repeat the start notification", async () => {
    const rtc = await startCallWithRecordingPermissions();
    patch(rtc, {
        addCallNotification({ id }) {
            if (id === "recording_started") {
                expect.step("recording started");
            }
        },
    });
    rtc.recordingState = { audio: true, transcription: false, video: true };
    rtc.recordingState = { audio: true, transcription: false, video: true };
    rtc.recordingState = { audio: true, transcription: true, video: true };
    rtc.recordingState = { audio: false, transcription: false, video: false };
    rtc.recordingState = { audio: true, transcription: false, video: true };
    expect.verifySteps(["recording started", "recording started"]);
});

test("a small screen keeps the microphone, the camera and a way out in its bar", async () => {
    await patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // The dropdown registers its click handler in a useEffect, so wait for it before clicking.
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Start Call'):count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='mute']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='quick-voice-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='camera-on']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='quick-video-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='More']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='disconnect']:count(1)");
    // Everything the wide bar spread across its own row and two separate menus is in this one.
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await waitFor("[name='share-screen']:count(1)");
    await waitFor("[name='raise-hand']:count(1)");
    await waitFor("[name='fullscreen']:count(1)");
    await waitFor("[name='change-layout']:count(1)");
    await waitForNone("[name='picture-in-picture']");
});

test("a small screen meeting has one More menu, not one per cluster", async () => {
    await patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Start Call'):count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    // No side actions cluster beside the call bar, hence no second "More" next to its own.
    await waitForNone(".o-mail-MeetingSideActions");
    await waitFor(".o-mail-Meeting button[title='More']:count(1)");
    // One bar that fits leaves nothing to scroll sideways to.
    const bar = queryFirst(".o-mail-Meeting-bar");
    expect(bar.scrollWidth).toBeLessThan(bar.clientWidth + 1);
    expect(getComputedStyle(bar).overflowX).toBe("visible");
    // The call actions and the thread actions are both behind it.
    await contains(".o-mail-Meeting button[title='More']:count(1)").click();
    await waitFor("[name='share-screen']:count(1)");
    await waitFor("[name='member-list']:count(1)");
});

test("start a recording alone in a call", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(1)");
    const rtc = getService("discuss.rtc");
    rtc.can_record_audio = true;
    rtc.can_record_video = true;
    patch(rtc, {
        SFU_CLIENT_STATE: { CONNECTED: "connected" },
        sfuClient: {
            state: "connected",
            setRecording(options) {
                expect(options).toEqual({ audio: true, transcription: false, video: true });
                expect.step("start recording");
                return true;
            },
        },
    });
    await contains(".o-discuss-CallActionList [name='more-action:call-layout']:count(1)").click();
    await contains(".o-dropdown-item[name='record-call']:count(1)").click();
    await contains(".o-discuss-RecordingDialog button:text('Start recording'):count(1)").click();
    expect.verifySteps(["start recording"]);
});

test("keep failed start and stop recording notifications distinct", async () => {
    const rtc = await startCallWithRecordingPermissions();
    patch(rtc, {
        SFU_CLIENT_STATE: { CONNECTED: "connected" },
        sfuClient: {
            state: "connected",
            setRecording: () => false,
        },
    });
    await contains(".o-discuss-CallActionList [name='more-action:call-layout']:count(1)").click();
    await contains(".o-dropdown-item[name='record-call']:count(1)").click();
    await contains(".o-discuss-RecordingDialog button:text('Start recording'):count(1)").click();
    await waitFor(".o-discuss-Call-notification:text('Recording is not allowed'):count(1)");
    rtc.recordingState = { audio: true, transcription: false, video: true };
    await waitFor(".o-discuss-CallRecordingIndicator:count(1)");
    await hover(".o-discuss-CallRecordingIndicator");
    await contains(
        ".o-discuss-CallRecordingIndicator button:text('Stop recording'):count(1)"
    ).click();
    await waitFor(".o-discuss-Call-notification:text('Recording is not allowed'):count(1)");
    await waitFor(
        ".o-discuss-Call-notification:text('You are not allowed to stop the recording'):count(1)"
    );
});

test("show a failure notification when stopping a recording request rejects", async () => {
    const rtc = await startCallWithRecordingPermissions();
    rtc.recordingState = { audio: true, transcription: false, video: true };
    patch(rtc, {
        SFU_CLIENT_STATE: { CONNECTED: "connected" },
        sfuClient: {
            state: "connected",
            setRecording: () => Promise.reject(new Error("transport failure")),
        },
    });
    await waitFor(".o-discuss-CallRecordingIndicator:count(1)");
    await hover(".o-discuss-CallRecordingIndicator");
    await contains(
        ".o-discuss-CallRecordingIndicator button:text('Stop recording'):count(1)"
    ).click();
    await waitFor(".o-discuss-Call-notification:text('Could not stop the recording'):count(1)");
});

test("show a failure notification when starting a recording request rejects", async () => {
    const rtc = await startCallWithRecordingPermissions();
    patch(rtc, {
        SFU_CLIENT_STATE: { CONNECTED: "connected" },
        sfuClient: {
            state: "connected",
            setRecording: () => Promise.reject(new Error("transport failure")),
        },
    });
    await contains(".o-discuss-CallActionList [name='more-action:call-layout']:count(1)").click();
    await contains(".o-dropdown-item[name='record-call']:count(1)").click();
    await contains(".o-discuss-RecordingDialog button:text('Start recording'):count(1)").click();
    await waitFor(".o-discuss-Call-notification:text('Could not start the recording'):count(1)");
});

test("recording stop notification persists until dismissed", async () => {
    const rtc = await startCallWithRecordingPermissions();
    await rtc._handleNetworkUpdates({
        detail: {
            name: "channel_info_change",
            payload: {
                state: { audio: false, transcription: false, video: false },
                stopCode: "recording_timeout",
            },
        },
    });
    const notification = ".o_notification:text('Recording stopped due to timeout')";
    await waitFor(`${notification} .o_notification_bar.bg-warning:count(1)`);
    await advanceTime(10_000);
    await waitFor(`${notification}:count(1)`);
    await contains(`${notification} .o_notification_close:count(1)`).click();
    await waitForNone(notification);
});

test("partial recording requests stop only when no output remains", async () => {
    const rtc = await startCallWithRecordingPermissions();
    rtc.recordingState = { audio: true, transcription: true, video: false };
    patch(rtc, {
        SFU_CLIENT_STATE: { CONNECTED: "connected" },
        sfuClient: {
            state: "connected",
            setRecording(options) {
                expect(options).toEqual({ transcription: false });
                expect.step("set recording");
                return false;
            },
        },
    });
    await rtc.setRecording({ transcription: false });
    await waitFor(".o-discuss-Call-notification:text('Recording is not allowed'):count(1)");
    await waitForNone(
        ".o-discuss-Call-notification:text('You are not allowed to stop the recording')"
    );
    rtc.recordingState = { audio: false, transcription: true, video: false };
    await rtc.setRecording({ transcription: false });
    await waitFor(
        ".o-discuss-Call-notification:text('You are not allowed to stop the recording'):count(1)"
    );
    expect.verifySteps(["set recording", "set recording"]);
});

test("stopping cancels a recording request waiting for an SFU connection", async () => {
    const rtc = await startCallWithRecordingPermissions();
    rtc.p2pService.disconnect();
    patch(rtc, {
        serverInfo: undefined,
        sfuClient: undefined,
        upgradeConnectionDebounce() {
            expect.step("upgrade connection");
        },
    });
    await rtc.setRecording({ audio: true });
    expect(rtc.recordingRequest).toEqual({ audio: true });
    await rtc.setRecording({ video: true });
    expect(rtc.recordingRequest).toEqual({ audio: true });
    await rtc.setRecording({ audio: false, transcription: false, video: false });
    expect(rtc.recordingRequest).toBe(null);
    await waitFor(".o-discuss-Call-notification:text('Could not stop the recording'):count(1)");
    await advanceTime(15_000);
    await waitForNone(".o-discuss-Call-notification:text('Could not start the recording')");
    expect.verifySteps(["upgrade connection"]);
});

test("a recording request expires when the SFU upgrade does not connect", async () => {
    const rtc = await startCallWithRecordingPermissions();
    patch(rtc, {
        serverInfo: undefined,
        sfuClient: undefined,
    });
    await rtc.setRecording({ audio: true, video: true });
    expect(rtc.recordingRequest).toEqual({ audio: true, video: true });
    await advanceTime(15_000);
    expect(rtc.recordingRequest).toBe(null);
    await waitFor(".o-discuss-Call-notification:text('Could not start the recording'):count(1)");
    await rtc.setRecording({ audio: true, video: true });
    expect(rtc.recordingRequest).toEqual({ audio: true, video: true });
});

test("a cancelled recording request does not expire its replacement", async () => {
    const rtc = await startCallWithRecordingPermissions();
    patch(rtc, {
        serverInfo: undefined,
        sfuClient: undefined,
        upgradeConnectionDebounce() {},
    });
    await rtc.setRecording({ audio: true, video: true });
    await advanceTime(10_000);
    await rtc.stopRecording();
    await rtc.setRecording({ transcription: true });
    await advanceTime(5_000);
    expect(rtc.recordingRequest).toEqual({ transcription: true });
    await waitForNone(".o-discuss-Call-notification:text('Could not start the recording')");
    await advanceTime(10_000);
    expect(rtc.recordingRequest).toBe(null);
    await waitFor(".o-discuss-Call-notification:text('Could not start the recording'):count(1)");
});

test("a recording request consumed by the SFU does not expire", async () => {
    const rtc = await startCallWithRecordingPermissions();
    patch(rtc, {
        serverInfo: undefined,
        sfuClient: undefined,
        upgradeConnectionDebounce() {},
    });
    await rtc.setRecording({ audio: true, video: true });
    patch(rtc, {
        SFU_CLIENT_STATE: { CONNECTED: "connected" },
        sfuClient: {
            state: "connected",
            setRecording(options) {
                expect(options).toEqual({ audio: true, video: true });
                expect.step("set recording");
                return true;
            },
        },
    });
    await rtc.setRecording(rtc.recordingRequest);
    expect(rtc.recordingRequest).toBe(null);
    await advanceTime(15_000);
    await waitForNone(".o-discuss-Call-notification:text('Could not start the recording')");
    expect.verifySteps(["set recording"]);
});

async function startCallWithRecordingPermissions() {
    const pyEnv = await startServer();
    onRpc("/mail/rtc/channel/upgrade_connection", () => {});
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "Alice" }),
        }),
        channel_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Mitchell Admin']:count(1)");
    const rtc = getService("discuss.rtc");
    rtc.can_record_audio = true;
    rtc.can_record_video = true;
    return rtc;
}

test("mobile UI", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockUserAgent("android");
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    expect(isMobileOS()).toBe(true);
    await waitForNone("[title='Share Screen']");
});

test("keep the `more` popover active when hovering it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(".o-discuss-CallActionList:count(1)");
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    const enterFullScreenSelector = "[name='fullscreen']";
    await waitFor(`${enterFullScreenSelector}:count(1)`);
    await hover(queryFirst(enterFullScreenSelector));
    await waitFor(`${enterFullScreenSelector}:count(1)`);
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
    await waitFor(".o-mail-DiscussContent-header:count(1)");
    await waitForNone("[title='Start Call']");
});

test("should not display call UI when no more members (self disconnect)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await contains(".o-discuss-CallActionList button[aria-label='Disconnect']:count(1)").click();
    await waitForNone(".o-discuss-Call");
});

test("show call UI in chat window when in call", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openMessagingMenu(MENU_ACTIVE_IDS.CHANNEL);
    await contains(".o-mail-NotificationItem-name:text('General'):count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitForNone(".o-discuss-Call");
    await contains(".o-mail-ChatWindow-header [title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await waitForNone(".o-mail-ChatWindow-header [title='Start Call']");
});

test("joining a video call from a chat window opens the wide meeting view", async () => {
    const { isBrowserFullscreen } = mockBrowserFullscreen();
    const pyEnv = await startServer();
    onRpc("/mail/rtc/session/notify_call_members", () => true);
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 2" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.rtc.session"].create({
        channel_id: channelId,
        channel_member_id: memberId,
    });
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']:count(1)").click();
    await contains(".o-mail-NotificationItem-name:text('Partner 2'):count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await contains(".o-mail-ChatWindow button[title='Join Video Call']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(".o-mail-Meeting:has(.o-discuss-Call):count(1)");
    await waitFor(
        ".o-discuss-Call-topNotifications .o-discuss-Call-notification:text('To minimize, press ESC'):count(1)"
    );
    expect(isBrowserFullscreen()).toBe(false);
});

test("starting a video call from a chat window opens the wide meeting view", async () => {
    const { isBrowserFullscreen } = mockBrowserFullscreen();
    const pyEnv = await startServer();
    onRpc("/mail/rtc/session/notify_call_members", () => true);
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 2" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await contains(".o_menu_systray i[aria-label='Messages']:count(1)").click();
    await contains(".o-mail-NotificationItem-name:text('Partner 2'):count(1)").click();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await contains(".o-mail-ChatWindow button[title='Start Video Call']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(".o-mail-Meeting:has(.o-discuss-Call):count(1)");
    await waitFor(
        ".o-discuss-Call-topNotifications .o-discuss-Call-notification:text('To minimize, press ESC'):count(1)"
    );
    expect(isBrowserFullscreen()).toBe(false);
});

test("starting a video call from the Discuss app opens the wide meeting view", async () => {
    const { isBrowserFullscreen } = mockBrowserFullscreen();
    const pyEnv = await startServer();
    onRpc("/mail/rtc/session/notify_call_members", () => true);
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Video Call']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)"); // opens wide, like in a chat window
    // "To minimize, press ESC" hint shown at the top of the call view
    await waitFor(
        ".o-discuss-Call-topNotifications .o-discuss-Call-notification:text('To minimize, press ESC'):count(1)"
    );
    expect(isBrowserFullscreen()).toBe(false); // not in fullscreen
});

test("starting a plain call from the Discuss app stays inline (no meeting view)", async () => {
    const pyEnv = await startServer();
    onRpc("/mail/rtc/session/notify_call_members", () => true);
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    mockService("mail.sound_effects", {
        play(name) {
            expect.step(`play - ${name}`);
        },
    });
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await expect.waitForSteps(["play - call-join"]); // call is fully joined, meeting-view decision is settled
    expect(rtc.isFullscreen).toBe(false); // stayed inline: no wide meeting view for a camera-less call
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
            expect.step(`sendBeacon_leave_call:${blobData.params.channel_id}`);
        }
    });

    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    // simulate page close
    await manuallyDispatchProgrammaticEvent(window, "pagehide");
    await expect.waitForSteps([`sendBeacon_leave_call:${channelId}`]);
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
            expect.step(`play - ${name}`);
        },
        stop(name) {
            expect.step(`stop - ${name}`);
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
        new Store()
            .add(pyEnv["discuss.channel.rtc.session"].browse(sessionId), {
                channel_member_id: { id: memberId },
            })
            .add(pyEnv["discuss.channel.member"].browse(memberId), {
                partner_id: { id: partnerId },
                channel_id: { id: channelId, model: "discuss.channel" },
                rtc_inviting_session_id: { id: sessionId },
            })
            .as_dict()
    );
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await waitFor(".o-discuss-CallInvitation button[title='Join Call']:count(1)");
    await expect.waitForSteps(["play - call-invitation"]);
    // Simulate stop receiving call invitation

    pyEnv["bus.bus"]._sendone(
        partner,
        "mail.record/insert",
        new Store()
            .add(pyEnv["discuss.channel.member"].browse(memberId), {
                rtc_inviting_session_id: false,
            })
            .as_dict()
    );
    await waitForNone(".o-discuss-CallInvitation");
    await expect.waitForSteps(["stop - call-invitation"]);
});

test("can share screen", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Share Screen']:count(1)").click();
    await waitFor("video:count(1)");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await contains("[title='Stop Sharing Screen']:count(1)").click();
    await waitForNone("video");
});

test("can share user camera", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video:count(1)");
    await contains("[title='Turn camera off']:count(1)").click();
    await waitForNone("video");
});

test("switching camera device updates the video element stream", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const env = await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video[type='camera']:count(1)");
    const videoEl = queryFirst("video[type='camera']");
    const initialStream = videoEl.srcObject;
    expect(initialStream).toBeInstanceOf(MediaStream);
    env.services["mail.store"].settings.cameraInputDeviceId = "mockVideoDeviceId";
    await waitUntil(() => videoEl.srcObject !== initialStream, {
        message: "the video element should be given the stream of the new camera device",
        timeout: 5000,
    });
    // same element, new stream: the camera never went off, only the stream was replaced
    expect(queryFirst("video[type='camera']")).toBe(videoEl);
    expect(videoEl.srcObject).toBeInstanceOf(MediaStream);
});

test("switch front/back camera in mobile", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    // Switch camera action is only available for mobiles
    mockUserAgent("android");
    expect(isMobileOS()).toBe(true);
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video[data-facing-mode='user']:count(1)");
    // A camera setting, so it lives with the camera settings rather than in the bar.
    await waitForNone(".o-discuss-CallActionList button[name='switch-camera']");
    await contains("button[aria-label='Video Settings']:count(1)").click();
    await contains(
        ".o-discuss-QuickVideoSettings button[aria-label='Switch Camera']:count(1)"
    ).click();
    await waitFor("video[data-facing-mode='environment']:count(1)");
});

test("Camera video stream stays in focus when on/off", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await contains("[title='Turn camera off']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video[type='camera']:not(.o-inset):count(1)");
    // test screen sharing then camera on to check camera aside
    await contains("[title='Turn camera off']:count(1)").click();
    await contains("[title='Share Screen']:count(1)").click();
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video[type='screen']:not(.o-inset):count(1)");
    await waitFor("video[type='camera'].o-inset:count(1)");
});

test("Create a direct message channel when clicking on start a meeting", async () => {
    mockDate("2026-01-01 10:00:00", "Asia/Kolkata");
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { tz: "Europe/Brussels" });
    const channelId = pyEnv["discuss.channel"].create({ name: "Slytherin" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "some message",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread:contains('Welcome to #Slytherin!'):count(1)");
    await waitFor(".o-mail-Message:count(1)");
    await contains(".o-mail-MessagingMenu-tab[data-id='meeting']:count(1)").click();
    await contains("button:text('Meeting'):count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".o-mail-MessagingMenuItem:has(:text('Meeting, Jan 1')):count(1)");
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(".o-mail-MeetingReadyBanner:count(1)");
    await waitFor(".o-mail-Meeting-clock:text('3:30 PM')[title='Jan 1, 2026, 3:30 PM']:count(1)");
    await waitFor(".o-mail-MeetingSideActions button:count(2)");
    await waitFor(".o-mail-MeetingSideActions button[title='Members']:count(1)");
    await waitFor(".o-mail-MeetingSideActions button[title='Chat']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='More']:count(1)");
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await waitFor("[name='fullscreen']:count(1)");
    await waitFor("[name='change-layout']:count(1)");
    await waitFor("[name='picture-in-picture']:count(1)");
});

test("Can share user camera and screen together", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Share Screen']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video:count(2)");
});

test("Click on inset card should replace the inset and active stream together", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Share Screen']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video[type='screen']:not(.o-inset):count(1)");
    await contains("video[type='camera'].o-inset:count(1)").click();
    await waitFor("video[type='screen'].o-inset:count(1)");
    await waitFor("video[type='camera']:not(.o-inset):count(1)");
});

test("Inset card is hidden when sidebar is open", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "Alice" }),
        }),
        channel_id: channelId,
    });
    await start();
    const store = getService("mail.store");
    store.settings.callLayout = CALL_GRID_LAYOUT.SPOTLIGHT;
    await openDiscuss(channelId);
    await click("[title='Join Call']");
    await click("[title='Turn camera on']");
    await click("[title='Share Screen']");
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await waitFor(".o-mail-Meeting:count(1)");
    await waitFor(".o-discuss-CallParticipantCard.o-inset:count(1)");
    // Sidebar visibility is driven solely by the layout: switching to it hides the inset.
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // reveal the floating overlay
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Sidebar')");
    expect(store.settings.callLayout).toBe(CALL_GRID_LAYOUT.SIDEBAR);
    await waitFor(".o-discuss-Call-sidebar:count(1)");
    await waitForNone(".o-discuss-CallParticipantCard.o-inset");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // reveal the floating overlay
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Spotlight')");
    expect(store.settings.callLayout).toBe(CALL_GRID_LAYOUT.SPOTLIGHT);
    await waitFor(".o-discuss-CallParticipantCard.o-inset:count(1)");
});

test("join/leave sounds are only played on main tab", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    listenStoreFetch("/mail/messaging_menu/discuss.channel/load_more");
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    patch(env1.services["mail.sound_effects"], {
        play(name) {
            expect.step(`tab1 - play - ${name}`);
        },
    });
    patch(env2.services["mail.sound_effects"], {
        play(name) {
            expect.step(`tab2 - play - ${name}`);
        },
    });
    await openDiscuss(channelId, { target: env1 });
    await waitStoreFetch("/mail/messaging_menu/discuss.channel/load_more");
    await openDiscuss(channelId, { target: env2 });
    await waitStoreFetch("/mail/messaging_menu/discuss.channel/load_more");
    await contains(`${env1.selector} [title='Start Call']:count(1)`).click();
    await waitFor(`${env1.selector} .o-discuss-Call:count(1)`);
    await waitFor(`${env2.selector} .o-discuss-Call:count(1)`);
    await expect.waitForSteps(["tab1 - play - call-join"]);
    await contains(`${env1.selector} [title='Disconnect']:not([disabled]):count(1)`).click();
    await waitForNone(`${env1.selector} .o-discuss-Call`);
    await waitForNone(`${env2.selector} .o-discuss-Call`);
    await expect.waitForSteps(["tab1 - play - call-leave"]);
});

test("'New Meeting' in mobile", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 2" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({ name: "Slytherin" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "some message",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread:contains('Welcome to #Slytherin!'):count(1)");
    await waitFor(".o-mail-Message:count(1)");
    await waitFor("button[title*='Close Chat Window']:count(1)");
    await click(".o-mail-MessagingMenu-tab[data-id='meeting']");
    await click("button:text('Meeting')");
    await click(".o-dropdown-item:text('Start Now')");
    await click(".o-mail-MeetingReadyBanner button:text('Add Others')");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Partner 2'))");
    await click("button:not([disabled]):text('Invite to Meeting')");
    await waitFor(".o-discuss-Call:count(1)");
    // A small screen has no side actions cluster: they live in the call bar's "More".
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='member-list']");
    await waitFor(".o-discuss-ChannelMember:text('Partner 2'):count(1)");
});

test("Dropzones below fullscreen meeting view are disabled", async () => {
    const { popoutIframe } = mockPipWindow();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 2" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({ name: "Slytherin" });
    pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            body: "msg-1",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "msg-2",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:count(2)");
    await contains(".o-mail-MessagingMenu-tab[data-id='meeting']:count(1)").click();
    await contains("button:text('Meeting'):count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    await contains(".o-mail-Meeting button[title='Chat']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen .o-mail-ActionPanel .o-mail-Thread:count(1)");
    const textFile_1 = new File(["hello, world"], "text-1.txt", { type: "text/plain" });
    await dragenterFiles(".o-mail-Meeting.o-fullscreen .o-mail-Thread", [textFile_1]);
    await waitFor(".o-Dropzone:count(1)"); // only dropzone in meeting view
    await dropFiles(".o-Dropzone", [textFile_1]);
    await waitFor(".o-mail-Meeting .o-mail-AttachmentContainer:not(.o-isUploading):count(1)");
    // check picture-in-picture still enables dropzone
    await contains(".o-mail-Meeting [title='More']:count(1)").click();
    await contains("[name='picture-in-picture']:count(1)").click();
    await mailContains(".o-mail-Meeting:not(.o-fullscreen)", {
        target: popoutIframe.contentDocument,
    });
    const textFile_2 = new File(["hello, world"], "text-2.txt", { type: "text/plain" });
    await dragenterFiles(".o-mail-Discuss .o-mail-Thread", [textFile_1]);
    await waitFor(".o-Dropzone:count(1)"); // only dropzone in discuss app
    await dropFiles(".o-Dropzone", [textFile_2]);
    await waitFor(".o-mail-Discuss .o-mail-AttachmentContainer:not(.o-isUploading):count(2)");
});

test("Fullscreen button enters browser fullscreen; the menu then offers Wide View", async () => {
    const fullscreen = mockBrowserFullscreen();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await waitFor("[name='fullscreen'][aria-label='Fullscreen']:count(1)");
    await waitFor("[name='wide-view'][aria-label='Wide View']:count(1)");
    await waitForNone("[name='minimize']");
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(fullscreen.isBrowserFullscreen()).toBe(true);
    expect(rtc.isBrowserFullscreen).toBe(true);
    await contains(".o-mail-Meeting [title='More']:count(1)").click();
    await waitForNone("[name='fullscreen']");
    await waitFor("[name='wide-view'][aria-label='Wide View']:count(1)");
    await waitFor("[name='minimize'][aria-label='Minimize']:count(1)");
    await contains("[name='wide-view']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(fullscreen.isBrowserFullscreen()).toBe(false);
    expect(rtc.isBrowserFullscreen).toBe(false);
    await waitFor(
        ".o-discuss-Call-topNotifications .o-discuss-Call-notification:text('To minimize, press ESC'):count(1)"
    );
    await contains(".o-mail-Meeting [title='More']:count(1)").click();
    await waitFor("[name='fullscreen'][aria-label='Fullscreen']:count(1)");
    await waitForNone("[name='wide-view']");
    await waitFor("[name='minimize'][aria-label='Minimize']:count(1)");
});

test("Fullscreen button label reflects a denied browser fullscreen request", async () => {
    const fullscreen = mockBrowserFullscreen({ grant: false });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    // The meeting still opens as the windowed overlay, but browser fullscreen was denied.
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(fullscreen.isBrowserFullscreen()).toBe(false);
    expect(rtc.isBrowserFullscreen).toBe(false);
    // The action keeps offering "Fullscreen" instead of wrongly showing "Exit Fullscreen".
    await contains(".o-mail-Meeting [title='More']:count(1)").click();
    await waitFor("[name='fullscreen'][aria-label='Fullscreen']:count(1)");
});

test("Leaving browser fullscreen externally (e.g. Escape) closes the meeting view", async () => {
    const fullscreen = mockBrowserFullscreen();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(rtc.isBrowserFullscreen).toBe(true);
    // The browser leaving fullscreen on its own is reflected declaratively and tears down the view.
    fullscreen.leaveBrowserFullscreen();
    await waitForNone(".o-mail-Meeting");
    expect(rtc.isBrowserFullscreen).toBe(false);
});

test("Closing picture-in-picture from browser fullscreen restores the windowed meeting view", async () => {
    const fullscreen = mockBrowserFullscreen();
    mockPipWindow();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(fullscreen.isBrowserFullscreen()).toBe(true);
    expect(rtc.isBrowserFullscreen).toBe(true);
    // Opening PiP leaves browser fullscreen and closes the meeting view in the main window.
    await contains(".o-mail-Meeting [title='More']:count(1)").click();
    await contains("[name='picture-in-picture']:count(1)").click();
    await waitForNone(".o-mail-Meeting");
    expect(fullscreen.isBrowserFullscreen()).toBe(false);
    // Closing PiP restores the meeting as the windowed overlay rather than re-entering browser
    // fullscreen, which would require a user gesture we cannot trigger programmatically.
    await rtc.closePip();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(fullscreen.isBrowserFullscreen()).toBe(false);
    expect(rtc.isBrowserFullscreen).toBe(false);
});

test("Minimize button leaves the meeting view like pressing Escape", async () => {
    const fullscreen = mockBrowserFullscreen();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(rtc.isBrowserFullscreen).toBe(true);
    await contains(".o-mail-Meeting [title='More']:count(1)").click();
    await contains("[name='minimize'][aria-label='Minimize']:count(1)").click();
    await waitFor(".o-mail-Discuss .o-discuss-Call:count(1)");
    await waitForNone(".o-mail-Meeting");
    expect(fullscreen.isBrowserFullscreen()).toBe(false);
    expect(rtc.isBrowserFullscreen).toBe(false);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='wide-view']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
    expect(rtc.isFullscreen).toBe(true);
    expect(rtc.isBrowserFullscreen).toBe(false);
    await press("escape");
    await waitFor(".o-mail-Discuss .o-discuss-Call:count(1)");
    await waitForNone(".o-mail-Meeting");
    expect(rtc.isFullscreen).toBe(false);
});

/**
 * @param {Object} pyEnv
 * @param {number} channelId
 * @param {string} name
 */
function createCallParticipant(pyEnv, channelId, name) {
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name }),
    });
    const sessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: channelMemberId,
        channel_id: channelId,
    });
    return { channelMemberId, sessionId };
}

async function openMeetingView() {
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='wide-view']:count(1)").click();
    await waitFor(".o-mail-Meeting.o-fullscreen:count(1)");
}

test("Leaving the meeting view brings the Discuss call back to its tiles", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    createCallParticipant(pyEnv, channelId, "Alice");
    createCallParticipant(pyEnv, channelId, "Bob");
    await start();
    const store = getService("mail.store");
    store.settings.callLayout = CALL_GRID_LAYOUT.SPOTLIGHT;
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(3)");
    await openMeetingView();
    await waitFor(".o-mail-Meeting .o-discuss-CallParticipantCard:count(1)");
    await press("escape"); // leave meeting view
    await waitForNone(".o-mail-Meeting");
    await waitFor(".o-mail-Discuss .o-discuss-CallParticipantCard:count(3)");
    expect(store.rtc.channel.activeRtcSession).toBe(undefined);
});

test("Leaving the meeting view keeps the pinned participant focused", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { sessionId: aliceSessionId } = createCallParticipant(pyEnv, channelId, "Alice");
    createCallParticipant(pyEnv, channelId, "Bob");
    await start();
    const store = getService("mail.store");
    store.settings.callLayout = CALL_GRID_LAYOUT.SPOTLIGHT;
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(3)");
    await openMeetingView();
    const channel = store.rtc.channel;
    channel.pin(channel.rtc_session_ids.find((session) => session.id === aliceSessionId));
    await press("escape"); // leave meeting view
    await waitForNone(".o-mail-Meeting");
    await waitFor(".o-mail-Discuss .o-discuss-CallParticipantCard[aria-label='Alice']:count(1)");
    await waitForNone(".o-mail-Discuss .o-discuss-CallParticipantCard[aria-label='Bob']");
    expect(channel.activeRtcSession.id).toBe(aliceSessionId);
});

test("Leaving the meeting view keeps a shared screen focused", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Streamer" }),
    });
    createCallParticipant(pyEnv, channelId, "Bob");
    const env = await start();
    const store = getService("mail.store");
    const network = await makeMockRtcNetwork({ env, channelId });
    const streamerRemote = network.makeMockRemote(channelMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await streamerRemote.updateConnectionState("connected");
    await waitFor(".o-discuss-CallParticipantCard:count(3)");
    await openMeetingView();
    await streamerRemote.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await waitFor(
        ".o-mail-Meeting .o-discuss-CallParticipantCard[aria-label='Streamer'] video:count(1)"
    );
    await press("escape"); // leave meeting view
    await waitForNone(".o-mail-Meeting");
    await waitFor(
        ".o-mail-Discuss .o-discuss-CallParticipantCard[aria-label='Streamer'] video:count(1)"
    );
    await waitForNone(".o-mail-Discuss .o-discuss-CallParticipantCard[aria-label='Bob']");
    expect(store.rtc.channel.activeRtcSession.mainVideoStreamType).toBe("screen");
});

test("Leaving the meeting view auto-focuses the participant video in a chat window", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: serverState.partnerId,
    });
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Batman" }),
    });
    setupChatHub({ opened: [channelId] });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const mockedRemote = network.makeMockRemote(channelMemberId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(2)");
    await mockedRemote.updateConnectionState("connected");
    await openMeetingView();
    await mockedRemote.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await waitFor(
        ".o-mail-Meeting .o-discuss-CallParticipantCard[aria-label='Batman'] video:count(1)"
    );
    await press("escape"); // leave meeting view
    await waitForNone(".o-mail-Meeting");
    await waitFor(
        ".o-mail-ChatWindow .o-discuss-CallParticipantCard[aria-label='Batman'] video:count(1)"
    );
    await waitFor(".o-mail-ChatWindow .o-discuss-CallParticipantCard:count(1)");
});

async function startCallWithMicWarningInPip() {
    mockPermissionsPrompt(); // overrides the "granted" mock from beforeEach
    const mocks = mockPipWindow();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Start Call')");
    await waitFor(".o-discuss-Call:count(1)");
    await click(".o-mail-ActionList-button[name='more-action:call-layout']");
    await click(".o-dropdown-item[name='picture-in-picture']");
    await mailContains(".o-mail-Meeting", { target: mocks.popoutIframe.contentDocument });
    await mailContains(".o_popover:contains('No microphone permissions')", {
        target: mocks.popoutIframe.contentDocument,
    });
    return mocks;
}

test("Leaving the call with mic warning in PiP, then rejoining, generates no error", async () => {
    await startCallWithMicWarningInPip();
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Disconnect')");
    await waitForNone(".o-discuss-Call");
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Start Call')");
    await waitFor(".o-discuss-Call:count(1)");
});

test("Closing PiP natively with mic warning, leaving, then rejoining, generates no error", async () => {
    const { popoutWindow } = await startCallWithMicWarningInPip();
    popoutWindow.close(); // the browser's close button: skips closePip()
    await advanceTime(POLL_CLOSE_WINDOW_TIMEOUT);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Disconnect')");
    await waitForNone(".o-discuss-Call");
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Start Call')");
    await waitFor(".o-discuss-Call:count(1)");
});

test("Systray icon shows latest action", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='mic']:count(1)");
    await click("[title='Mute']");
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='mic_off']:count(1)");
    await click("[title='Voice Settings']");
    await click(".dropdown-menu button:contains('Deafen')");
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='hearing_disabled']:count(1)");
    await click("[title='Turn camera on']");
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='videocam']:count(1)");
    await click("[title='Share Screen']");
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='desktop_windows']:count(1)");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click("[title='Raise Hand']");
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='back_hand']:count(1)");
});

test("Can use Call actions in Call Systray Menu", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click(".o-discuss-CallMenu-actionsButton");
    await waitFor(".o-dropdown-item:count(9)");
    await waitFor(".o-dropdown-item:has(:text('Mute')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Deafen')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Turn camera on')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Share Screen')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Raise Hand')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Picture in Picture')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Fullscreen')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Wide View')):count(1)");
    await waitFor(".o-dropdown-item:has(:text('Disconnect')):count(1)");
});

test("Systray icon keeps track of earlier actions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='mic']:count(1)");
    await contains("[title='Share Screen']:count(1)").click();
    // stack: ["share-screen"]
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='desktop_windows']:count(1)");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await contains("[title='Turn camera on']:count(1)").click();
    // stack: ["video", "share-screen"]
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='videocam']:count(1)");
    await contains("[title='Mute']:count(1)").click();
    // stack: ["mute", "video", "share-screen"]
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='mic_off']:count(1)");
    await contains("[title='Unmute']:count(1)").click();
    // stack: ["video", "share-screen"]
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='videocam']:count(1)");
    await contains("[title='Turn camera off']:count(1)").click();
    // stack: ["share-screen"]
    await waitFor(".o-discuss-CallMenu-buttonContent [data-icon='desktop_windows']:count(1)");
});

test("show call participants in discuss sidebar", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text('General')) .o-mail-MessagingMenuCallParticipants img[title='Mitchell Admin']:count(1)"
    );
});

test("Sort call participants by name", async () => {
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
    await contains("[title='Expand participants'][data-icon='chevron_forward']:count(1)").click();
    await mailContains(".o-mail-MessagingMenuCallParticipants", {
        contains: [
            ".o-mail-MessagingMenuCallParticipants-participant:nth-child(1):contains('AAA')",
        ],
    });
    await mailContains(".o-mail-MessagingMenuCallParticipants", {
        contains: [
            ".o-mail-MessagingMenuCallParticipants-participant:nth-child(2):contains('BBB')",
        ],
    });
    await mailContains(".o-mail-MessagingMenuCallParticipants", {
        contains: [
            ".o-mail-MessagingMenuCallParticipants-participant:nth-child(3):contains('CCC')",
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
        { name: "Jack" },
        { name: "Kate" },
        { name: "Jane" },
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
    await waitFor(".o-mail-MessagingMenuCallParticipants img:count(10)");
    await waitFor("img[title='Alice']:count(1)");
    await waitFor("img[title='Bob']:count(1)");
    await waitFor("img[title='Cathy']:count(1)");
    await waitFor("img[title='David']:count(1)");
    await waitFor("img[title='Eric']:count(1)");
    await waitFor("img[title='Frank']:count(1)");
    await waitFor("img[title='Grace']:count(1)");
    await waitFor("img[title='Henry']:count(1)");
    await waitFor("img[title='Ivy']:count(1)");
    await waitFor("img[title='Jack']:count(1)");
    await waitFor(".o-mail-AvatarStack-remainingCount:text('+2'):count(1)");
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-mail-MessagingMenuCallParticipants img:count(13)");
    await waitFor("img[title='Alice']:count(1)");
    await waitFor("img[title='Bob']:count(1)");
    await waitFor("img[title='Cathy']:count(1)");
    await waitFor("img[title='David']:count(1)");
    await waitFor("img[title='Eric']:count(1)");
    await waitFor("img[title='Frank']:count(1)");
    await waitFor("img[title='Grace']:count(1)");
    await waitFor("img[title='Henry']:count(1)");
    await waitFor("img[title='Ivy']:count(1)");
    await waitFor("img[title='Jack']:count(1)");
    await waitFor("img[title='Jane']:count(1)");
    await waitFor("img[title='Kate']:count(1)");
    await waitFor("img[title='Mitchell Admin']:count(1)");
});

test("Clicking call participant opens avatar card", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(
        ".o-mail-MessagingMenuCallParticipants-participant:text('Mitchell Admin'):count(1)"
    ).click();
    await waitFor(".o-mail-avatar-card-name:text('Mitchell Admin'):count(1)");
});

test("call participant shows appropriate status icon", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const bobMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "bob" }),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const bobRemote = network.makeMockRemote(bobMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await bobRemote.updateConnectionState("connected");
    await waitFor(".o-discuss-Call:count(1)");
    await contains("button[title='Mute']:count(1)").click();
    await waitFor(
        ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] [data-icon='mic_off']:count(1)"
    );
    await waitFor(
        ".o-mail-MessagingMenuCallParticipants:contains('Mitchell Admin') [data-icon='mic_off']:count(1)"
    );
    await waitFor("button[title='Unmute']:count(1)");
    await contains("button[title='Voice Settings']:count(1)").click();
    await contains(".dropdown-menu button:contains('Deafen'):count(1)").click();
    await waitFor(
        ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] [data-icon='hearing_disabled']:count(1)"
    );
    await waitForNone(
        ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] [data-icon='mic_off']"
    );
    await waitFor(
        ".o-mail-MessagingMenuCallParticipants:contains('Mitchell Admin') [data-icon='hearing_disabled']:count(1)"
    );
    await waitForNone(
        ".o-mail-MessagingMenuCallParticipants:contains('Mitchell Admin') [data-icon='mic_off']"
    );
    await contains("button[title='Undeafen']:count(1)").click();
    await waitForNone(
        ".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] [data-icon='hearing_disabled']"
    );
    await waitForNone(
        ".o-mail-MessagingMenuCallParticipants:contains('Mitchell Admin') [data-icon='hearing_disabled']"
    );
    await bobRemote.updateInfo({ is_muted: true });
    await waitFor(
        ".o-mail-MessagingMenuCallParticipants:contains('bob') [data-icon='mic_off']:count(1)"
    );
    await bobRemote.updateInfo({ is_deaf: true });
    await waitFor(
        ".o-mail-MessagingMenuCallParticipants:contains('bob') [data-icon='hearing_disabled']:count(1)"
    );
});

test("deafen and undeafen from the bar of a small screen", async () => {
    await patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Start Call'):count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='mute'][aria-label='Mute']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='quick-voice-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='camera-on']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='quick-video-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='More']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='disconnect']:count(1)");

    // Deafening hides the microphone toggle, so the bar needs "deafen" to keep an audio control.
    await contains(
        ".o-discuss-CallActionList button[aria-label='Voice Settings']:count(1)"
    ).click();
    await contains(".dropdown-menu button:contains('Deafen'):count(1)").click();
    await waitFor(
        ".o-discuss-CallActionList button[name='deafen'][aria-label='Undeafen']:count(1)"
    );
    await waitFor(".o-discuss-CallActionList button[name='quick-voice-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='camera-on']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='quick-video-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='More']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='disconnect']:count(1)");

    await contains(".o-discuss-CallActionList button[name='deafen']:count(1)").click();
    await waitFor(".o-discuss-CallActionList button[name='mute'][aria-label='Mute']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='quick-voice-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='camera-on']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='quick-video-settings']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='More']:count(1)");
    await waitFor(".o-discuss-CallActionList button[name='disconnect']:count(1)");
});

test("collapsed call participants show who is talking", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const bobMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "bob" }),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const bobRemote = network.makeMockRemote(bobMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await bobRemote.updateConnectionState("connected");
    await contains("[title='Collapse participants']:count(1)").click();
    await bobRemote.updateInfo({ isTalking: true });
    await waitFor(".o-mail-MessagingMenuCallParticipants img[title='bob'].o-isTalking:count(1)");
    await bobRemote.updateInfo({ isTalking: false });
    await waitFor(
        ".o-mail-MessagingMenuCallParticipants img[title='bob']:not(.o-isTalking):count(1)"
    );
});

test("start call when accepting from push notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss();
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", {
            data: { action: "OPEN_CHANNEL", data: { id: channelId, joinCall: true } },
        })
    );
    await waitFor(".o-mail-DiscussContent-threadName[title=General]:count(1)");
    await waitFor(
        `.o-discuss-CallParticipantCard[aria-label='${serverState.partnerName}']:count(1)`
    );
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
    await contains("[title='Join the Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await waitFor(
        `.o-discuss-CallParticipantCard[aria-label='${partnerName}'][data-is-context-menu-available]:count(1)`
    );
    await hover(`.o-discuss-CallParticipantCard[aria-label='${partnerName}']`);
    await contains("button[title='Participant options']:count(1)").click();
    await waitFor(".o-discuss-CallContextMenu:count(1)");
    const rangeInput = queryFirst(".o-discuss-CallContextMenu input[type='range']");
    expect(rangeInput.value).toBe(expectedVolume.toString());
    rangeInput.dispatchEvent(new Event("change")); // to trigger the volume change
    await contains(".o-discuss-CallActionList button[aria-label='Disconnect']:count(1)").click();
});

test("show call participants after stopping screen share", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Share Screen']:count(1)").click();
    await waitFor("video:count(1)");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await contains("[title='Stop Sharing Screen']:count(1)").click();
    await waitForNone("video");
    // when all participant cards are shown they are minimized
    await waitFor(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard-avatar .o-minimized:count(1)"
    );
});

test("show call participants after stopping camera share", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor("video:count(1)");
    await contains("[title='Turn camera off']:count(1)").click();
    await waitForNone("video");
    // when all participant cards are shown they are minimized
    await waitFor(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard-avatar .o-minimized:count(1)"
    );
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
    expect("[title='Mute']").not.toHaveCount();
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
    await waitFor("[title='Disconnect']:count(1)");
    await waitFor("[title='Mute']:count(1)");

    broadcastChannel.onmessage = (event) => {
        if (event.data.type === CROSS_TAB_CLIENT_MESSAGE.REQUEST_ACTION) {
            expect.step(`is_muted:${event.data.changes["is_muted"]}`);
        }
    };
    await contains("[title='Mute']:count(1)").click();
    await expect.waitForSteps(["is_muted:true"]);
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
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await advanceTime(30_000);
    await waitForNone(".o-discuss-CallInvitation");
});

test("Should not auto-cancel incoming call when camera preview is open", async () => {
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
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await advanceTime(ChannelMember.CANCEL_CALL_INVITE_DELAY - 5000);
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await contains(".o-mail-ActionList-button[title='Show camera preview']:count(1)").click();
    await advanceTime(ChannelMember.CANCEL_CALL_INVITE_DELAY - 5000); // Call should not auto-cancel while preview is open
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await contains(".o-mail-ActionList-button[title='Hide camera preview']:count(1)").click();
    await advanceTime(ChannelMember.CANCEL_CALL_INVITE_DELAY); // Timer restarts when the preview closes, and the call should auto-cancel after 30s.
    await waitForNone(".o-discuss-CallInvitation");
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
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await contains("button[title='Add People']:count(1)").click();
    await waitFor(
        ".o-discuss-ChannelInvitation:has(:text('Invite people to the channel \"TestChanel\"')):count(1)"
    );
    await contains(
        ".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner')):count(1)"
    ).click();
    await contains("button:text('Invite'):enabled:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard.o-isInvitation:count(1)");
});

test("can join / leave call from discuss sidebar actions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Start Call')");
    await waitFor(".o-discuss-Call:count(1)");
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Disconnect')");
    await waitForNone(".o-discuss-Call");
});

test("shows warning on infinite mirror effect (screen-sharing then fullscreen)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='Share Screen']");
    await waitFor("video:count(1)");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await waitFor(".o-discuss-Call-mainCards h1:contains('You are Presenting'):count(1)");
    await waitFor("button:contains('Show My Screen Anyway'):count(1)");
    await waitFor(
        ".o-discuss-CallPresentationBar-container button[aria-label='Stop presenting']:count(1)"
    );
    await waitFor(".o-discuss-CallParticipantCard button[aria-label='Stop Presenting']:count(1)");
});

test("single 'join' (without camera) button when last call was audio-only", async () => {
    const pyEnv = await startServer();
    onRpc("/mail/rtc/session/notify_call_members", () => true);
    const alfredPartnerId = pyEnv["res.partner"].create({ name: "Alfred" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: alfredPartnerId }),
        ],
    });
    const [alfredMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", alfredPartnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.rtc.session"].create({
        channel_id: channelId,
        channel_member_id: alfredMemberId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("button[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-Call.o-selfInCall:count(1)");
    await contains("button[title='Disconnect']:count(1)").click();
    await click("button[title='Join Call']:text('Join')", { contains: ["[data-icon='phone_f']"] });
});

test("single 'join' (with camera) button when last call had camera on", async () => {
    const pyEnv = await startServer();
    onRpc("/mail/rtc/session/notify_call_members", () => true);
    const alfredPartnerId = pyEnv["res.partner"].create({ name: "Alfred" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: alfredPartnerId }),
        ],
    });
    const [alfredMemberId] = pyEnv["discuss.channel.member"].search([
        ["partner_id", "=", alfredPartnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.rtc.session"].create({
        channel_id: channelId,
        channel_member_id: alfredMemberId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("button[title='Join Video Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Mitchell Admin'] video:count(1)");
    await contains("button[title='Disconnect']:count(1)").click();
    await click("button[title='Join Video Call']:text('Join')", {
        contains: ["[data-icon='videocam_f']"],
    });
});

test("dynamic focus switches to talking participant", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const aliceSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "Alice" }),
        }),
        channel_id: channelId,
    });
    const bobSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "Bob" }),
        }),
        channel_id: channelId,
    });

    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Mitchell Admin']:count(1)");
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Bob']:count(1)");
    rtc.channel.activeRtcSession = rtc.channel.rtc_session_ids.find(
        (session) => session.id === aliceSessionId
    );
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Alice']:count(1)");
    await waitForNone(".o-discuss-CallParticipantCard[aria-label='Bob']");
    rtc.updateSessionInfo({ [bobSessionId]: { isTalking: true } });
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Bob']:count(1)");
    rtc.updateSessionInfo({ [aliceSessionId]: { isTalking: true } });
    await waitForNone(".o-discuss-CallParticipantCard[aria-label='Bob']");
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Alice']:count(1)");
    rtc.updateSessionInfo({ [aliceSessionId]: { isTalking: false } });
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Bob']:count(1)");
    await hover(".o-discuss-CallParticipantCard[aria-label='Bob']");
    await contains("button[aria-label='Video Settings']:count(1)").click();
    await contains(
        ".o-discuss-QuickVideoSettings button:has(:text('Advanced Settings')):count(1)"
    ).click();
    await waitFor(
        ".o-discuss-CallSettings .o-mail-TabHeader.o-active:has(:text('Video')):count(1)"
    );
    await contains("input[title='Auto-focus speaker']:checked:count(1)").click();
});

test("Shows warning badge on mic/camera on non-granted permission in meeting conversations", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "Bob" }),
        }),
        channel_id: channelId,
    });
    await start();
    const rtc = getService("discuss.rtc");
    rtc.microphonePermission = "denied";
    rtc.cameraPermission = "denied";
    await openDiscuss(channelId);
    await waitFor(".o-mail-DiscussContent-threadName[title='General']:count(1)");
    await contains(".o-mail-MessagingMenu-tab[data-id='meeting']:count(1)").click();
    await contains("button:text('Meeting'):count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    await waitFor("button[title='Turn camera off']:count(1)");
    await waitFor("button[title='Turn camera off'].o-tag-DANGER:count(1)");
    await waitFor("button[title='Turn camera off'].o-tag-WARNING_BADGE:count(1)");
    await rtc.exitFullscreen();
    await contains(".o-mail-MessagingMenu-tab[data-id='channel']:count(1)").click();
    await contains(".o-mail-NotificationItem:has(:text('General')):count(1)").click();
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(
        ".modal:has(:text('Switch to the other call? This will disconnect you from your ongoing call.')):count(1)"
    );
    await contains(".modal-footer button:text('Switch'):count(1)").click();
    await waitFor("button[title='Turn camera on']:count(1)");
    await waitForNone("button[title='Turn camera on'].o-tag-DANGER");
    await waitForNone("button[title='Turn camera on'].o-tag-WARNING_BADGE");
    await contains("button[title='Disconnect']:count(1)").click();
    await waitNotifications(["discuss.channel.rtc.session/ended"]);
});

test("only notified of a call disconnection when the server ends the session", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patch(Rtc.prototype, {
        notifyServerDisconnect() {
            expect.step("notifyServerDisconnect");
            return super.notifyServerDisconnect(...arguments);
        },
    });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    // Delay the response so that the session removal broadcast by the server is processed
    // before the client knows that the leave request succeeded.
    let respondToLeave;
    onRpcAfter("/mail/rtc/channel/leave_call", () => new Promise((res) => (respondToLeave = res)));
    await contains("[title='Disconnect']:count(1)").click();
    await waitNotifications(["discuss.channel.rtc.session/ended"]);
    respondToLeave();
    await waitForNone(".o-discuss-Call");
    await expect.waitForSteps([]);
    // A session removal that does not come from leaving locally is a server disconnection.
    await contains("[title='Start Call']:enabled:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    pyEnv["discuss.channel.rtc.session"].unlink([getService("discuss.rtc").selfSession.id]);
    await waitForNone(".o-discuss-Call");
    await waitFor(".o_notification:text('Disconnected from the call by the server'):count(1)");
    await expect.waitForSteps(["notifyServerDisconnect"]);
});

test("should not show context menu on participant card when not in a call", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "group",
        name: "General",
    });
    pyEnv["discuss.channel.rtc.session"].create([
        {
            channel_member_id: pyEnv["discuss.channel.member"].create({
                channel_id: channelId,
                partner_id: pyEnv["res.partner"].create({ name: "Awesome Partner" }),
            }),
            channel_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Awesome Partner']:count(1)");
    await waitForNone(
        ".o-discuss-CallParticipantCard[aria-label='Awesome Partner'][data-is-context-menu-available]"
    );
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(
        ".o-discuss-CallParticipantCard[aria-label='Awesome Partner'][data-is-context-menu-available]:count(1)"
    );
    await hover(".o-discuss-CallParticipantCard[aria-label='Awesome Partner']");
    await contains(
        ".o-discuss-CallParticipantCard[aria-label='Awesome Partner'] .o-discuss-CallParticipantCard-contextButton:count(1)"
    ).click();
    await waitFor(".o-discuss-CallContextMenu:count(1)");
});

test("all streams are properly closed when abruptly disconnected", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    const audioStream = streams.at(-1);
    expect(audioStream.getTracks()[0].readyState).toBe("live");
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard video:count(1)");
    const cameraStream = streams.at(-1);
    expect(cameraStream.getTracks()[0].readyState).toBe("live");
    await contains("[title='Share Screen']:count(1)").click();
    await waitFor("[title='You are presenting']:count(1)");
    const screenStream = streams.at(-1);
    expect(screenStream.getTracks()[0].readyState).toBe("live");
    expect(streams.length).toBe(3);
    pyEnv["discuss.channel.rtc.session"].unlink([rtc.selfSession.id]);
    await waitForNone(".o-discuss-Call");
    expect(audioStream.getTracks()[0].readyState).toBe("ended");
    expect(cameraStream.getTracks()[0].readyState).toBe("ended");
    expect(screenStream.getTracks()[0].readyState).toBe("ended");
});

test("Leaving a call should close all the streams", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard video:count(1)");
    await contains("[title='Share Screen']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard.o-inset:count(1)");
    expect(streams.length).toBe(3);
    expect(streams[0].getTracks()[0].readyState).toBe("live");
    expect(streams[1].getTracks()[0].readyState).toBe("live");
    expect(streams[2].getTracks()[0].readyState).toBe("live");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await contains(".o-discuss-CallActionList button[aria-label='Disconnect']:count(1)").click();
    await waitForNone(".o-discuss-Call");
    expect(streams[0].getTracks()[0].readyState).toBe("ended");
    expect(streams[1].getTracks()[0].readyState).toBe("ended");
    expect(streams[2].getTracks()[0].readyState).toBe("ended");
});

test("all streams are properly closed when requesting new ones and tuning the features off", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    const audioStream = streams.at(-1);
    expect(audioStream.getTracks()[0].readyState).toBe("live");
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard video:count(1)");
    const cameraStream1 = streams.at(-1);
    expect(cameraStream1.getTracks()[0].readyState).toBe("live");
    await contains("[title='Turn camera off']:count(1)").click();
    await waitForNone(".o-discuss-CallParticipantCard video");
    await contains("[title='Turn camera on']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard video:count(1)");
    const cameraStream2 = streams.at(-1);
    expect(cameraStream1.getTracks()[0].readyState).toBe("ended");
    expect(cameraStream2.getTracks()[0].readyState).toBe("live");
    await contains("[title='Turn camera off']:count(1)").click();
    await waitForNone(".o-discuss-CallParticipantCard video");
    await contains("[title='Share Screen']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard video:count(1)");
    await waitFor(".o-discuss-CallPresentationBar:count(1)");
    const screenStream = streams.at(-1);
    expect(screenStream.getTracks()[0].readyState).toBe("live");
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await contains("[title='Stop Sharing Screen']:count(1)").click();
    expect(screenStream.getTracks()[0].readyState).toBe("ended");
});

test("Show connecting state on cards", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Bob" }),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const bobRemote = network.makeMockRemote(channelMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Bob']:count(1)");
    await bobRemote.updateConnectionState("connecting");
    await waitFor(
        ".o-discuss-CallParticipantCard[aria-label='Bob'] [data-icon='warning']:count(1)"
    );
    await bobRemote.updateConnectionState("connected");
    await waitFor("span[data-connection-state='connected']:count(1)");
});

test("Can see raised hands from other call participants", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Bob" }),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const bobRemote = network.makeMockRemote(channelMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Bob']:count(1)");
    await bobRemote.updateConnectionState("connected");
    await bobRemote.updateInfo({ isRaisingHand: true });
    await waitFor(
        ".o-discuss-CallParticipantCard[aria-label='Bob'] [data-icon='back_hand']:count(1)"
    );
    await waitFor(".o-discuss-Call-notification:contains('Bob raised their hand'):count(1)");
});

test("Can see videos from other call participants", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Bob" }),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const bobRemote = network.makeMockRemote(channelMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Bob']:count(1)");
    await bobRemote.updateConnectionState("connected");
    await bobRemote.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Bob'] video:count(1)");
});

test("show all participants on other user stops screen share", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Streamer" }),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const streamerRemote = network.makeMockRemote(channelMemberId);
    await openDiscuss(channelId);
    await contains("[title='Join Call']:count(1)").click();
    await streamerRemote.updateConnectionState("connected");
    await waitFor(".o-discuss-CallParticipantCard-avatar:count(2)");
    await streamerRemote.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await waitFor(".o-discuss-CallParticipantCard-avatar:count(2)");
    await waitFor(".o-discuss-CallParticipantCard video:count(1)");
    await contains(".o-discuss-CallParticipantCard[aria-label='Streamer'] video:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard-avatar:count(1)");
    await waitFor(".o-discuss-CallParticipantCard video:count(1)");
    await streamerRemote.updateUpload("screen", null);
    await waitFor(".o-discuss-CallParticipantCard-avatar:count(2)");
});

test("auto-focus participant video in one-to-one call in chat window", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: serverState.partnerId,
    });
    const channelMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({ name: "Batman" }),
    });
    setupChatHub({ opened: [channelId] });
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const mockedRemote = network.makeMockRemote(channelMemberId);
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(2)");
    await mockedRemote.updateConnectionState("connected");
    await mockedRemote.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Batman'] video:count(1)");
    await waitFor(".o-discuss-CallParticipantCard:count(1)");
    await mockedRemote.updateUpload("camera", null);
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting[data-active]:count(1)");
    await mockedRemote.updateUpload("camera", createVideoStream().getVideoTracks()[0]);
    await waitFor(".o-discuss-CallParticipantCard[aria-label='Batman'] video:count(1)");
    await waitFor(".o-discuss-CallParticipantCard:count(2)"); // card does not get focused in meeting view
});

test.tags("focus required");
test("open conversation from call invitation (chat window)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const [memberId] = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId]]);
    const rtcSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: memberId,
        channel_id: channelId,
    });
    pyEnv["discuss.channel.member"].write([memberId], { rtc_inviting_session_id: rtcSessionId });
    await start();
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await contains(".o-mail-CallInvitation-avatar:count(1)").click();
    await waitFor(".o-mail-ChatWindow .o-mail-Composer.o-focused:count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-mail-ChatWindow");
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-mail-ChatWindow .o-mail-Composer.o-focused:count(1)");
});

test("open conversation from call invitation (discuss app)", async () => {
    const pyEnv = await startServer();
    const channelId1 = pyEnv["discuss.channel"].create({ name: "General" });
    const channelId2 = pyEnv["discuss.channel"].create({ name: "Test" });
    const memberId = pyEnv["discuss.channel.member"].search([["channel_id", "=", channelId1]]);
    const rtcSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId1,
            partner_id: pyEnv["res.partner"].create({ name: "Armstrong" }),
        }),
        channel_id: channelId1,
    });
    pyEnv["discuss.channel.member"].write(memberId, { rtc_inviting_session_id: rtcSessionId });
    await start();
    await openDiscuss(channelId2);
    await waitFor(".o-mail-DiscussContent-threadName[title='Test']:count(1)");
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await contains(".o-mail-CallInvitation-avatar:count(1)").click();
    await waitFor(".o-mail-DiscussContent-threadName[title=General]:count(1)");
    await contains(".o-mail-NotificationItem:has(:text('Test')):count(1)").click();
    await waitFor(".o-discuss-CallInvitation:count(1)");
    await contains("[title='Join Call']:count(1)").click();
    await waitFor(".o-mail-DiscussContent-threadName[title=General]:count(1)");
});

test("Meeting chat panel excludes call notifications for 'New Meeting' channels", async () => {
    mockDate("2026-01-01 10:00:00");
    const pyEnv = await startServer();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await contains("[title='New Meeting']:count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".o-mail-MeetingReadyBanner:count(1)");
    await press("escape");
    await waitFor(".o-mail-Thread:has(:text('Meeting, Jan 1')):count(1)");
    const messages = pyEnv["mail.message"].search_read([["message_type", "=", "notification"]]);
    const time = deserializeDateTime(messages.at(-1).date).toLocaleString(
        luxon.DateTime.TIME_SIMPLE,
        { locale: user.lang }
    );
    await waitFor(
        `.o-mail-NotificationMessage:text('Mitchell Admin started a call.${time}'):count(1)`
    );
    await rtc.enterFullscreen();
    await waitFor(".o-mail-Meeting:count(1)");
    await contains("[title='Chat']:count(1)").click();
    await waitFor(".o-mail-ActionPanel-header:text('In call messages'):count(1)");
    await waitFor(".o-mail-Meeting .o-mail-Thread:has(:text('Meeting, Jan 1')):count(1)");
    await waitForNone(`.o-mail-NotificationMessage:text('Mitchell Admin started a call.${time}')`);
});

test("active call with a recording shows a processing link", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
        ],
        channel_type: "channel",
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        body: '<div data-oe-type="call" class="o_mail_notification"></div>',
        message_type: "notification",
        model: "discuss.channel",
        res_id: channelId,
    });
    const callHistoryId = pyEnv["discuss.call.history"].create({
        channel_id: channelId,
        has_recording: true,
        start_call_message_id: messageId,
        start_dt: "2026-01-01 10:00:00",
    });
    mockService("action", {
        doAction(action) {
            if (action.res_model !== "discuss.call.history") {
                return super.doAction(...arguments);
            }
            expect(action).toEqual({
                type: "ir.actions.act_window",
                res_model: "discuss.call.history",
                views: [[false, "form"]],
                res_id: callHistoryId,
            });
            expect.step("open recording");
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-NotificationMessage div:text('A recording is being processed and will be available here.'):count(1)"
    );
    await contains(
        `.o-mail-NotificationMessage a[href='/odoo/discuss.call.history/${callHistoryId}']:text('here'):count(1)`
    ).click();
    await expect.waitForSteps(["open recording"]);
});

test("shows a presenter bar when screen-sharing in discuss calls and meetings", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create([{ name: "Mario" }, { name: "John" }]);
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const memberIds = pyEnv["discuss.channel.member"].create([
        { channel_id: channelId, partner_id: partnerIds[0] },
        { channel_id: channelId, partner_id: partnerIds[1] },
    ]);
    const env = await start();
    const network = await makeMockRtcNetwork({ env, channelId });
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    const remotes = memberIds.map((memberId) => network.makeMockRemote(memberId));
    for (const remote of remotes) {
        await remote.updateConnectionState("connected");
    }
    await contains("button[title='Share Screen']:count(1)").click();
    rtc.screenAudioTrack = streams.at(-1).getTracks()[0];
    await waitFor(".o-discuss-CallPresentationBar:count(1)");
    await waitFor(
        ".o-discuss-CallPresentationBar-presenterLabel:text('You are presenting'):count(1)"
    );
    await remotes[0].updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await waitFor(
        ".o-discuss-CallPresentationBar-presenterLabel:text('You and Mario are presenting'):count(1)"
    );
    await waitFor(
        ".o-discuss-CallPresentationBar-presentationAudioContainer input[role='switch']:count(1)"
    );
    await remotes[1].updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await waitFor(
        ".o-discuss-CallPresentationBar-presenterLabel:text('You, Mario and 1 more are presenting'):count(1)"
    );
    await contains("button[aria-label='Stop presenting']:count(1)").click();
    await waitFor(
        ".o-discuss-CallPresentationBar-presenterLabel:text('Mario and John are presenting'):count(1)"
    );
    await waitForNone(
        ".o-discuss-CallPresentationBar-presentationAudioContainer input[role='switch']"
    );
    await waitForNone("button[aria-label='Stop presenting']");
    for (const remote of remotes) {
        await remote.updateUpload("screen", null);
    }
    await waitForNone(".o-discuss-CallPresentationBar");
});

test("Escape closes meeting UI layers sequentially", async () => {
    /** Escape closes overlay elements → action panel → fullscreen meeting view. */
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    await contains("[title='Chat']:count(1)").click();
    await waitFor(".o-mail-ActionPanel-header:text('In call messages'):count(1)");
    await contains(".o-mail-DiscussContent-panelContainer [title='Add Emojis']:count(1)").click();
    await waitFor(".o-EmojiPicker:count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-EmojiPicker ");
    await waitFor(".o-mail-DiscussContent-panelContainer .o-mail-Composer.o-focused:count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-mail-ActionPanel-header:text('In call messages')");
    await waitFor(".o-mail-Meeting:count(1)");
    triggerHotkey("Escape");
    await waitForNone(".o-mail-Meeting");
    await waitFor(".o-discuss-Call:count(1)");
});

test("Access to Pinned Messages from Meeting Chat", async () => {
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await click("button:text(Meeting)");
    await click(".o-dropdown-item:text('Start Now')");
    await waitFor(".o-mail-MeetingReadyBanner:count(1)");
    await click("[title='Chat']");
    await waitFor(".o-mail-ActionPanel-header:has(:text('In call messages')):count(1)");
    await insertText(".o-mail-Meeting .o-mail-Composer-input", "hey");
    await click(".o-mail-Meeting .o-mail-Composer button[title='Send']:enabled");
    await hover(".o-mail-Meeting .o-mail-Message");
    await click(".o-mail-Meeting .o-mail-Message [title='Expand']");
    await click(".dropdown-item:text('Pin')");
    await click(".modal-footer button:text('Pin Message')");
    await waitFor(
        ".o-mail-ActionPanel-header:has(:text('In call messages')) button[title='Pinned Messages'] .badge:text('1'):count(1)"
    );
    await click(".o-mail-ActionPanel-header button[title='Pinned Messages']");
    await waitFor(".o-mail-ActionPanel-header:has(:text('Pinned Messages')):count(1)");
});

test("show warning when blur hardware acceleration is not available", async () => {
    const pyEnv = await startServer();
    patch(HTMLCanvasElement.prototype, {
        getContext(type) {
            if (type.includes("webgl")) {
                return false;
            }
            return super.getContext(type);
        },
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("button[title='Turn camera on']");
    await click("button[title='Video Settings']");
    await click(":has(:text(Blur background)) .form-switch");
    await waitFor(".o-discuss-BlurPerformanceWarning-button:count(1)");
    expect(".o-discuss-BlurPerformanceWarning-button").toBeVisible();
    await waitFor(".o-discuss-CallDropdown-content:has(:text('Performance Warning:')):count(1)");
    expect(".o-discuss-CallDropdown-content:has(:text('Performance Warning:'))").toBeVisible();
    await click("[title='Dismiss warning']");
    await waitForNone(".o-discuss-BlurPerformanceWarning-button");
});

test("Adjust view: switching between Tiled and Spotlight changes the meeting grid", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    for (const name of ["Alice", "Bob"]) {
        pyEnv["discuss.channel.rtc.session"].create({
            channel_member_id: pyEnv["discuss.channel.member"].create({
                channel_id: channelId,
                partner_id: pyEnv["res.partner"].create({ name }),
            }),
            channel_id: channelId,
        });
    }
    await start();
    const store = getService("mail.store");
    store.settings.callLayout = "auto";
    await openDiscuss(channelId);
    await click("[title='Join Call']");
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await waitFor(".o-mail-Meeting:count(1)");
    // 3 participants with "auto" resolve to tiled: every card is shown in the grid.
    await waitFor(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard:count(3)");
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Spotlight')");
    expect(store.settings.callLayout).toBe("spotlight");
    // Spotlight collapses the grid to a single focused card.
    await waitFor(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard:count(1)");
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Tiled')");
    expect(store.settings.callLayout).toBe("tiled");
    await waitFor(".o-discuss-Call-mainCards .o-discuss-CallParticipantCard:count(3)");
});

test("Change layout dialog closes when the call is removed by the server", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='change-layout']:count(1)").click();
    await waitFor(".o-discuss-ChangeLayoutDialog:count(1)");
    // Server ends the call while the dialog is still open: it must close itself, otherwise its
    // layout actions would operate on the now-gone call and crash on the next click.
    pyEnv["discuss.channel.rtc.session"].unlink([rtc.selfSession.id]);
    await waitForNone(".o-discuss-ChangeLayoutDialog");
});

test("Auto layout switches to the sidebar while someone is presenting", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const store = getService("mail.store");
    store.settings.callLayout = "auto";
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click("[title='Share Screen']");
    await waitFor("video:count(1)");
    // Sharing makes self the active session, so the controller floats: reveal the overlay.
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]); // show overlay
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='fullscreen']");
    await waitFor(".o-mail-Meeting:count(1)");
    // On auto, presenting puts the shared screen in the main window and everyone in the sidebar.
    await waitFor(".o-discuss-Call-sidebar:count(1)");
    // Stopping the presentation reverts the auto layout (a lone participant is not a sidebar).
    await click(".o-discuss-CallPresentationBar-container button[aria-label='Stop presenting']");
    await waitForNone(".o-discuss-Call-sidebar");
});

test("Adjust view: sidebar layout always shows the sidebar, even alone", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const store = getService("mail.store");
    store.settings.callLayout = "sidebar";
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    // Sidebar mode always shows the sidebar column, even with a single participant.
    await waitFor(".o-discuss-Call-sidebar:count(1)");
});

test("Auto layout spotlights whoever joins a call, when self was alone in the call", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const store = getService("mail.store");
    store.settings.callLayout = "auto";
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    // Alone, self is the spotlight.
    await waitFor(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Mitchell Admin']:count(1)"
    );
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "Bob" }),
        }),
        channel_id: channelId,
    });
    // Whoever joins takes the spotlight over. Without any video, self gets no inset.
    await waitFor(
        ".o-discuss-Call-mainCards .o-discuss-CallParticipantCard[aria-label='Bob']:count(1)"
    );
    await waitForNone(".o-discuss-CallParticipantCard[aria-label='Mitchell Admin']");
});

test("confirm before switching calls", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "channel" }, { name: "channel2" }]);
    await start();
    await openDiscuss(channelIds[0]);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallMenu-channelInfo:text('channel'):count(1)");
    await contains(".o-mail-NotificationItem-name:text('channel2'):count(1)").click();
    await waitFor(".o-mail-AutoresizeInput[title='channel2']:count(1)");
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(
        ".modal:has(:text('Switch to the other call? This will disconnect you from your ongoing call.')):count(1)"
    );
    await contains(".modal-footer button:text('Cancel'):count(1)").click();
    await waitForNone(".modal");
    await waitFor(".o-discuss-CallMenu-channelInfo:text('channel'):count(1)");
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(
        ".modal:has(:text('Switch to the other call? This will disconnect you from your ongoing call.')):count(1)"
    );
    await contains(".modal-footer button:text('Switch'):count(1)").click();
    await waitFor(".o-discuss-CallMenu-channelInfo:text('channel2'):count(1)");
});

test("meeting ready banner is hidden in chat but shown in channel", async () => {
    mockBrowserFullscreen();
    let meeting;
    patch(Meeting.prototype, {
        setup() {
            super.setup();
            meeting = this;
        },
    });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(chatId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    await waitUntil(() => meeting?.channel?.id === chatId);
    expect(meeting.showInviteBanner).toBe(false);
    await waitForNone(".o-mail-MeetingReadyBanner");
    await contains(".o-mail-Meeting [title='Disconnect']:count(1)").click();
    await contains(".o-mail-MessagingMenu-tab[data-id='channel']:count(1)").click();
    await contains(".o-mail-NotificationItem-name:text('General'):count(1)").click();
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await contains("[name='fullscreen']:count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    await waitUntil(() => meeting?.channel?.id === channelId);
    expect(meeting.showInviteBanner).toBe(true);
    await waitFor(".o-mail-MeetingReadyBanner button:text('Add Others'):count(1)");
});
