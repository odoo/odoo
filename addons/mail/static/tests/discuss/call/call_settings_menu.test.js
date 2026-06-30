import {
    click,
    contains,
    defineMailModels,
    editInput,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, expect } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { asyncStep, patchWithCleanup, waitForSteps } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";

describe.current.tags("desktop");
defineMailModels();

test("Renders the call settings", async () => {
    patchWithCleanup(browser.navigator.mediaDevices, {
        enumerateDevices: () =>
            Promise.resolve([
                {
                    deviceId: "mockAudioDeviceId",
                    kind: "audioinput",
                    label: "mockAudioDeviceLabel",
                },
                {
                    deviceId: "mockVideoDeviceId",
                    kind: "videoinput",
                    label: "mockVideoDeviceLabel",
                },
            ]),
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains(".o-discuss-CallSettings");
    await contains("label[aria-label='Camera']");
    await contains("label[aria-label='Microphone']");
    await contains("label[aria-label='Audio Output']");
    await contains("option", { textContent: "Permission Needed", count: 3 });
    rtc.microphonePermission = "granted";
    await contains("option[value=mockAudioDeviceId]");
    rtc.cameraPermission = "granted";
    await contains("option[value=mockVideoDeviceId]");
    await contains("button", { text: "Voice Detection" });
    await contains("button", { text: "Push to Talk" });
    await contains("span", { text: "Voice detection sensitivity" });
    await contains("button", { text: "Test" });
    await contains("label", { text: "Show video participants only" });
    await contains("label", { text: "Blur video background" });
});

test("activate push to talk", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("button", { text: "Push to Talk" });
    await contains("i[aria-label='Register new key']");
    await contains("label", { text: "Delay after releasing push-to-talk" });
    await contains("label", { text: "Voice detection sensitivity", count: 0 });
});

test("activate blur", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("input[title='Blur video background']");
    await contains("label", { text: "Blur video background" });
    await contains("label", { text: "Edge blur intensity" });
});

test("local storage for call settings", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail_user_setting_background_blur_amount", "3");
    localStorage.setItem("mail_user_setting_edge_blur_amount", "5");
    localStorage.setItem("mail_user_setting_show_only_video", "true");
    localStorage.setItem("mail_user_setting_use_blur", "true");
    patchWithCleanup(localStorage, {
        setItem(key, value) {
            if (key.startsWith("mail_user_setting")) {
                asyncStep(`${key}: ${value}`);
            }
            return super.setItem(key, value);
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // testing load from local storage
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains("input[title='Show video participants only']:checked");
    await contains("input[title='Blur video background']:checked");
    await contains("label[title='Background blur intensity']", { text: "15%" });
    await contains("label[title='Edge blur intensity']", { text: "25%" });

    // testing save to local storage
    await click("input[title='Show video participants only']");
    await waitForSteps(["mail_user_setting_show_only_video: false"]);
    await click("input[title='Blur video background']");
    expect(localStorage.getItem("mail_user_setting_use_blur")).toBe(null);
    await editInput(document.body, ".o-Discuss-CallSettings-thresholdInput", 0.3);
    await advanceTime(2000); // threshold setting debounce timer
    await waitForSteps(["mail_user_setting_voice_threshold: 0.3"]);
});
