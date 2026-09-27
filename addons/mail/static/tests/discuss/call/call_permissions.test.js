import {
    click,
    contains,
    defineMailModels,
    MENU_ACTIVE_IDS,
    mockGetMedia,
    mockPermissionsPrompt,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { getService } from "@web/../tests/web_test_helpers";

import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("Starting a video call asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await click("[title='Start Video Call']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.cameraPermission = "granted";
    await click(".modal-footer button:text('Use camera')");
    await contains(".o-discuss-CallActionList button[title='Turn camera off']");
});

test("Starting a meeting asks for microphone permission", async () => {
    await startServer();
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await click("[title='New Meeting']");
    await click(".o-dropdown-item:text('Start Now')");
    await contains(".modal-footer button", { count: 2 });
    await contains(".modal-footer button:text('Use microphone and camera')");
    await contains(".modal-footer button:text('Use microphone')");
    rtc.microphonePermission = "granted";
    await click(".modal-footer button:text('Use microphone')");
    await contains(".o-discuss-CallActionList button[title='Mute']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
});

test("Starting a meeting with camera granted asks for microphone permission", async () => {
    await startServer();
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    rtc.cameraPermission = "granted";
    await click("[title='New Meeting']");
    await click(".o-dropdown-item:text('Start Now')");
    await contains(".o-discuss-CallActionList button[title='Turn camera off']");
    await contains(".modal-footer button");
    await contains(".modal-footer button:text('Use microphone')");
});

test("Starting a meeting with microphone granted asks for camera permission", async () => {
    await startServer();
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    rtc.microphonePermission = "granted";
    await click("[title='New Meeting']");
    await click(".o-dropdown-item:text('Start Now')");
    await contains(".modal-footer button");
    await contains(".modal-footer button:text('Use camera')");
});

test("Turning on the microphone asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
    await click(".o-discuss-CallActionList button[title='Unmute']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.microphonePermission = "granted";
    await click(".modal-footer button:text('Use microphone')");
    await contains(".o-discuss-CallActionList button[title='Mute']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
});

test("Turning on the camera asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.cameraPermission = "granted";
    await click(".modal-footer button:text('Use camera')");
    await contains(".o-discuss-CallActionList button[title='Turn camera off']");
});

test("Turn on both microphone and camera from permission dialog", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.microphonePermission = "granted";
    rtc.cameraPermission = "granted";
    await click(".modal-footer button:text('Use microphone and camera')");
    await contains(".o-discuss-CallActionList button[title='Turn camera off']");
    await contains(".o-discuss-CallActionList button[title='Mute']");
});

test("Combined mic+camera button only shown when both permissions not granted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal-footer button", { count: 2 });
    await contains(".modal-footer button:text('Use microphone and camera')");
    await contains(".modal-footer button:text('Use camera')");
    rtc.cameraPermission = "granted";
    await click(".modal-footer button:text('Use camera')");
    await click(".o-discuss-CallActionList button[title='Unmute']");
    await contains(".modal-footer button");
    await contains(".modal-footer button:text('Use microphone')");
});

test("Microphone permission warning is hidden while the permission dialog is open", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o_popover:text('No microphone permissions')");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal:has(:text('Do you want people to see you in the meeting?'))");
    await contains(".o_popover", { count: 0 });
    // leaving the call closes the permission dialog, the warning comes back in the next call
    await click(".o-discuss-CallActionList button[aria-label='Disconnect']");
    await contains(".modal", { count: 0 });
    await click("[title='Start Call']");
    await contains(".o_popover:text('No microphone permissions')");
    // dismissing the dialog without granting the permission brings the warning back
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal:has(:text('Do you want people to see you in the meeting?'))");
    await contains(".o_popover", { count: 0 });
    await click(".modal .btn-close");
    await contains(".modal", { count: 0 });
    await contains(".o_popover:text('No microphone permissions')");
    // granting the permissions from the dialog leaves no warning behind
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal:has(:text('Do you want people to see you in the meeting?'))");
    rtc.cameraPermission = "granted";
    rtc.microphonePermission = "granted";
    await click(".modal-footer button:text('Use microphone and camera')");
    await contains(".o-discuss-CallActionList button[title='Turn camera off']");
    await contains(".o_popover", { count: 0 });
});
