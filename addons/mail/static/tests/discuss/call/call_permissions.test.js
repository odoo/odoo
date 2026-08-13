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

test("Starting a new meeting asks for microphone permission", async () => {
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
    rtc.microphonePermission = "granted";
    await click(".modal-footer button:text('Use microphone')");
    await contains(".o-discuss-CallActionList button[title='Mute']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
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
