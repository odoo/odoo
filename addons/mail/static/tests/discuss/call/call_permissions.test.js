import {
    click,
    contains,
    defineMailModels,
    focus,
    mockGetMedia,
    mockPermissionsPrompt,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("Starting a video call asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    await openDiscuss(channelId);
    await click("[title='Start Video Call']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.cameraPermission = "granted";
    await click(".modal-footer button", { text: "Use Camera" });
    await contains(".o-discuss-CallActionList button[title='Stop camera']");
});

test("Turning on the microphone asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
    await click(".o-discuss-CallActionList button[title='Unmute']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.microphonePermission = "granted";
    await click(".modal-footer button", { text: "Use Microphone" });
    await contains(".o-discuss-CallActionList button[title='Mute']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
});

test("Turning on the camera asks for permissions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.cameraPermission = "granted";
    await click(".modal-footer button", { text: "Use Camera" });
    await contains(".o-discuss-CallActionList button[title='Stop camera']");
});

test("Turn on both microphone and camera from permission dialog", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal[role='dialog']", { count: 1 });
    rtc.microphonePermission = "granted";
    rtc.cameraPermission = "granted";
    await click(".modal-footer button", { text: "Use microphone and camera" });
    await contains(".o-discuss-CallActionList button[title='Stop camera']");
    await contains(".o-discuss-CallActionList button[title='Mute']");
});

test("Combined mic+camera button only shown when both permissions not granted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click(".o-discuss-CallActionList button[title='Turn camera on']");
    await contains(".modal-footer button", { count: 2 });
    await contains(".modal-footer button", { text: "Use microphone and camera" });
    await contains(".modal-footer button", { text: "Use Camera" });
    rtc.cameraPermission = "granted";
    await click(".modal-footer button", { text: "Use Camera" });
    await click(".o-discuss-CallActionList button[title='Unmute']");
    await contains(".modal-footer button");
    await contains(".modal-footer button", { text: "Use Microphone" });
});

test("Pressing Escape key on voice & video wizard does not trigger permission dialog", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockGetMedia();
    mockPermissionsPrompt();
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    await openDiscuss(channelId);
    await contains(".o-mail-Composer.o-focused");
    await click("[title='Start Call']");
    await click(".o-discuss-CallActionList button[aria-label='Voice Settings']");
    await click(".dropdown-menu button:has(:text('Voice Settings'))");
    await contains(".o-discuss-CallSettings select[name='inputDevice']:first");
    rtc.microphonePermission = "denied";
    rtc.cameraPermission = "denied";
    await focus(".o-discuss-CallSettings select[name='inputDevice']:first");
    triggerHotkey("Enter");
    await contains(".o_notification:contains('access blocked. Enable in browser settings.')");
    await contains(".o-discuss-CallSettings");
    await click(".o_notification_close");
    await contains(".o_notification", { count: 0 });
    await focus(".o-discuss-CallSettings select[name='inputDevice']:first");
    triggerHotkey("Tab");
    await contains(".o_notification", { count: 0 });
    await contains(".o-discuss-CallSettings");
    triggerHotkey("Escape");
    await contains(".o-discuss-CallSettings", { count: 0 });
    await contains(".o_notification", { count: 0 });
});
