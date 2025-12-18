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
import { parseRawValue, toRawValue } from "@mail/utils/common/local_storage";
import { Settings } from "@mail/core/common/settings_model";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { describe, test, expect } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { isBrowserChrome } from "@web/core/browser/feature_detection";

describe.current.tags("desktop");
defineMailModels();

test("Renders the call settings", async () => {
    patchWithCleanup(browser.navigator.mediaDevices, {
        enumerateDevices: () => {
            const deviceList = [
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
            ];
            if (isBrowserChrome()) {
                deviceList.push({
                    deviceId: "default",
                    kind: "audioinput",
                    label: "Default",
                });
            }
            return Promise.resolve(deviceList);
        },
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
    await click(".o-dropdown-item:text('Call Settings')");
    await contains(".o-discuss-CallSettings");
    await contains("label[aria-label='Camera']");
    await contains("label[aria-label='Microphone']");
    await contains("label[aria-label='Speakers']");
    await contains(".o-mail-DeviceSelect-button:has(:text('Permission Needed'))", { count: 3 });
    rtc.microphonePermission = "granted";
    const browserDefaultLabel = isBrowserChrome() ? "Default" : "Browser Default";
    await click(".o-mail-DeviceSelect-button[data-kind='audioinput']:has(:text('Default'))");
    await contains(".o-dropdown-item:has(:text('mockAudioDeviceLabel'))");
    await contains(`.o-dropdown-item:has(:text(${browserDefaultLabel}))`);
    rtc.cameraPermission = "granted";
    await click(".o-mail-DeviceSelect-button[data-kind='videoinput']:has(:text('Default'))");
    await contains(".o-dropdown-item:has(:text('mockVideoDeviceLabel'))");
    await contains(`.o-dropdown-item:has(:text(${browserDefaultLabel}))`);
    await contains("button:text('Voice Detection')");
    await contains("button:text('Push to Talk')");
    await contains("span:text('Voice detection sensitivity')");
    await contains(".o-discuss-CallSettings button:text('Test')");
    await contains("label:text('Show video participants only')");
    await contains("label:text('Auto-focus speaker')");
    await contains("label:text('Blur video background')");
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
    await click(".o-dropdown-item:text('Call Settings')");
    await click("button:text('Push to Talk')");
    await contains("i[aria-label='Register new key']");
    await contains("label:has(:text('Delay after releasing push-to-talk'))");
    await contains("span:text('Voice detection sensitivity')", { count: 0 });
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
    await click(".o-dropdown-item:text('Call Settings')");
    await click("input[title='Blur video background']");
    await contains("label:has(:text('Blur video background'))");
    await contains("label:has(:text('Edge blur intensity'))");
});

test("local storage for call settings", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const backgroundBlurAmountKey = makeRecordFieldLocalId(
        Settings.localId(),
        "backgroundBlurAmount"
    );
    localStorage.setItem(backgroundBlurAmountKey, toRawValue(3));
    const edgeBlurAmountKey = makeRecordFieldLocalId(Settings.localId(), "edgeBlurAmount");
    localStorage.setItem(edgeBlurAmountKey, toRawValue(5));
    const showOnlyVideoKey = makeRecordFieldLocalId(Settings.localId(), "showOnlyVideo");
    localStorage.setItem(showOnlyVideoKey, toRawValue(true));
    const useBlurLocalStorageKey = makeRecordFieldLocalId(Settings.localId(), "useBlur");
    localStorage.setItem(useBlurLocalStorageKey, toRawValue(true));
    const callSettingsKeys = [
        "Settings,undefined:backgroundBlurAmount",
        "Settings,undefined:edgeBlurAmount",
        "Settings,undefined:showOnlyVideo",
        "Settings,undefined:voiceActivationThreshold",
    ];
    patchWithCleanup(localStorage, {
        setItem(key, value) {
            if (callSettingsKeys.includes(key)) {
                expect.step(`${key}: ${parseRawValue(value).value}`);
            }
            return super.setItem(key, value);
        },
        removeItem(key) {
            if (callSettingsKeys.includes(key)) {
                expect.step(`${key}: removed`);
            }
            return super.removeItem(key);
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // testing load from local storage
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Call Settings')");
    await contains("input[title='Show video participants only']:checked");
    await contains("input[title='Blur video background']:checked");
    await contains("label[title='Background blur intensity']:has(:text('15%'))");
    await contains("label[title='Edge blur intensity']:has(:text('25%'))");

    // testing save to local storage
    await click("input[title='Show video participants only']");
    await expect.waitForSteps(["Settings,undefined:showOnlyVideo: removed"]);
    await click("input[title='Blur video background']");
    expect(localStorage.getItem(useBlurLocalStorageKey)).toBe(null);
    await editInput(document.body, ".o-Discuss-CallSettings-thresholdInput", 0.3);
    await expect.waitForSteps(["Settings,undefined:voiceActivationThreshold: 0.3"]);
});
