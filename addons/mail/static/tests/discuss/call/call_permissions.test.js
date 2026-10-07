import {
    defineMailModels,
    MENU_ACTIVE_IDS,
    mockGetMedia,
    mockPermissionsPrompt,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { contains, getService } from "@web/../tests/web_test_helpers";

import { describe, test, waitFor, waitForNone } from "@odoo/hoot";

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
    await contains("[title='Start Video Call']:count(1)").click();
    await waitFor(".modal[role='dialog']:count(1)");
    rtc.cameraPermission = "granted";
    await contains(".modal-footer button:text('Use camera'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera off']:count(1)");
});

test("Starting a meeting asks for microphone permission", async () => {
    await startServer();
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await contains("[title='New Meeting']:count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".modal-footer button:count(2)");
    await waitFor(".modal-footer button:text('Use microphone and camera'):count(1)");
    await waitFor(".modal-footer button:text('Use microphone'):count(1)");
    rtc.microphonePermission = "granted";
    await contains(".modal-footer button:text('Use microphone'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Mute']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='Turn camera on']:count(1)");
});

test("Starting a meeting with camera granted asks for microphone permission", async () => {
    await startServer();
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    rtc.cameraPermission = "granted";
    await contains("[title='New Meeting']:count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera off']:count(1)");
    await waitFor(".modal-footer button:count(1)");
    await waitFor(".modal-footer button:text('Use microphone'):count(1)");
});

test("Starting a meeting with microphone granted asks for camera permission", async () => {
    await startServer();
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    rtc.microphonePermission = "granted";
    await contains("[title='New Meeting']:count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".modal-footer button:count(1)");
    await waitFor(".modal-footer button:text('Use camera'):count(1)");
});

test("Turning on the microphone asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera on']:count(1)");
    await contains(".o-discuss-CallActionList button[title='Unmute']:count(1)").click();
    await waitFor(".modal[role='dialog']:count(1)");
    rtc.microphonePermission = "granted";
    await contains(".modal-footer button:text('Use microphone'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Mute']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='Turn camera on']:count(1)");
});

test("Turning on the camera asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='Turn camera on']:count(1)").click();
    await waitFor(".modal[role='dialog']:count(1)");
    rtc.cameraPermission = "granted";
    await contains(".modal-footer button:text('Use camera'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera off']:count(1)");
});

test("Turn on both microphone and camera from permission dialog", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera on']:count(1)");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']:count(1)").click();
    await waitFor(".modal[role='dialog']:count(1)");
    rtc.microphonePermission = "granted";
    rtc.cameraPermission = "granted";
    await contains(".modal-footer button:text('Use microphone and camera'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera off']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='Mute']:count(1)");
});

test("Combined mic+camera button only shown when both permissions not granted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains(".o-discuss-CallActionList button[title='Turn camera on']:count(1)").click();
    await waitFor(".modal-footer button:count(2)");
    await waitFor(".modal-footer button:text('Use microphone and camera'):count(1)");
    await waitFor(".modal-footer button:text('Use camera'):count(1)");
    rtc.cameraPermission = "granted";
    await contains(".modal-footer button:text('Use camera'):count(1)").click();
    await contains(".o-discuss-CallActionList button[title='Unmute']:count(1)").click();
    await waitFor(".modal-footer button:count(1)");
    await waitFor(".modal-footer button:text('Use microphone'):count(1)");
});

test("Microphone permission warning is hidden while the permission dialog is open", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o_popover:text('No microphone permissions'):count(1)");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']:count(1)").click();
    await waitFor(".modal:has(:text('Do you want people to see you in the meeting?')):count(1)");
    await waitForNone(".o_popover");
    // leaving the call closes the permission dialog, the warning comes back in the next call
    await contains(".o-discuss-CallActionList button[aria-label='Disconnect']:count(1)").click();
    await waitForNone(".modal");
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o_popover:text('No microphone permissions'):count(1)");
    // dismissing the dialog without granting the permission brings the warning back
    await contains(".o-discuss-CallActionList button[title='Turn camera on']:count(1)").click();
    await waitFor(".modal:has(:text('Do you want people to see you in the meeting?')):count(1)");
    await waitForNone(".o_popover");
    await contains(".modal .btn-close:count(1)").click();
    await waitForNone(".modal");
    await waitFor(".o_popover:text('No microphone permissions'):count(1)");
    // granting the permissions from the dialog leaves no warning behind
    await contains(".o-discuss-CallActionList button[title='Turn camera on']:count(1)").click();
    await waitFor(".modal:has(:text('Do you want people to see you in the meeting?')):count(1)");
    rtc.cameraPermission = "granted";
    rtc.microphonePermission = "granted";
    await contains(".modal-footer button:text('Use microphone and camera'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera off']:count(1)");
    await waitForNone(".o_popover");
});
