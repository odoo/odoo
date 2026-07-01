import {
    click,
    contains,
    defineMailModels,
    editInput,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { parseRawValue, toRawValue } from "@mail/utils/common/local_storage";
import { Settings } from "@mail/core/common/settings_model";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { describe, keyDown, mockDate, test, expect } from "@odoo/hoot";
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
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await contains(".o-discuss-CallSettings");
    await contains("div[aria-label='Microphone']");
    await contains("div[aria-label='Speakers']");
    await contains(".o-mail-DeviceSelect-button:has(:text('Click to activate'))", { count: 2 });
    rtc.microphonePermission = "granted";
    const browserDefaultLabel = isBrowserChrome() ? "Default" : "Browser Default";
    await click(".o-mail-DeviceSelect-button[data-kind='audioinput']:has(:text('Default'))");
    await contains(".o-dropdown-item:text('mockAudioDeviceLabel')");
    await contains(`.o-dropdown-item:text(${browserDefaultLabel})`);
    await contains("label[aria-label='Enable Push-to-talk']");
    await contains("input[title='Voice detection sensitivity']");
    await contains(".o-discuss-CallSettings button:text('Test')");
    await click("button[title='Video']");
    await contains("div[aria-label='Camera']");
    await contains(".o-mail-DeviceSelect-button:has(:text('Click to activate'))");
    rtc.cameraPermission = "granted";
    await click(".o-mail-DeviceSelect-button[data-kind='videoinput']:has(:text('Default'))");
    await contains(".o-dropdown-item:text('mockVideoDeviceLabel')");
    await contains(`.o-dropdown-item:text(${browserDefaultLabel})`);
    await contains("label span:text('Auto-focus speaker')");
    await contains("label span:text('Blur video background')");
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
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await contains("input[title='Voice detection sensitivity']");
    await click("label[aria-label='Enable Push-to-talk']");
    await contains("input[title='Delay after releasing push-to-talk']");
    await contains("input[title='Voice detection sensitivity']", { count: 0 });
    // ensure push to talk settings updates reflect in UI
    await click("button[aria-label='Register new shortcut']");
    await keyDown("Ctrl+m");
    await contains("button[aria-label='Register new shortcut']:text('Ctrl+m')");
    await contains(".o-discuss-CallSettings-voiceActiveDuration:text('200ms')");
    await editInput(document.body, ".o-discuss-CallSettings-delayInput", 560);
    await contains(".o-discuss-CallSettings-voiceActiveDuration:text('560ms')");
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
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await click("button[title='Video']");
    await click("input[title='Blur video background']");
    await contains("div[title='Background blur intensity'] span:has(:text('Intensity'))");
    await contains("div[title='Edge blur intensity'] span:has(:text('Edge Softness'))");
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
    const useBlurLocalStorageKey = makeRecordFieldLocalId(Settings.localId(), "useBlur");
    localStorage.setItem(useBlurLocalStorageKey, toRawValue(true));
    const voiceActivationThresholdKey = makeRecordFieldLocalId(
        Settings.localId(),
        "voiceActivationThreshold"
    );
    const callSettingsKeys = [
        backgroundBlurAmountKey,
        edgeBlurAmountKey,
        voiceActivationThresholdKey,
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
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await contains("label[aria-label='Enable Push-to-talk']");
    await editInput(document.body, "input[title='Voice detection sensitivity']", 0.3);
    await expect.waitForSteps([`${voiceActivationThresholdKey}: 0.3`]);
    await click("button[title='Video']");
    await contains("input[title='Blur video background']:checked");
    await contains("div[title='Background blur intensity']:has(:text('15%'))");
    await contains("div[title='Edge blur intensity']:has(:text('25%'))");
    await click("input[title='Blur video background']");
    expect(localStorage.getItem(useBlurLocalStorageKey)).toBe(null);
});

test("Adjust view dialog: each layout option and the prioritize-video toggle persist the setting", async () => {
    mockGetMedia();
    mockDate("2026-01-01 10:00:00");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const env = await start();
    const store = env.services["mail.store"];
    await openDiscuss(channelId);
    await click(".o-mail-MessagingMenu-tab[data-id='meeting']");
    await click("button:text('Meeting')");
    await contains(".o-mail-Meeting");
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await contains(".o-discuss-ChangeLayoutDialog");
    await contains(".o-discuss-ChangeLayoutDialog-option", { count: 5 });
    // Each grid layout is persisted and reflected as the selected row.
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Tiled')");
    expect(store.settings.callLayout).toBe("tiled");
    await contains(".o-discuss-ChangeLayoutDialog-option.o-selected:contains('Tiled')");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Spotlight')");
    expect(store.settings.callLayout).toBe("spotlight");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Sidebar')");
    expect(store.settings.callLayout).toBe("sidebar");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Auto (dynamic)')");
    expect(store.settings.callLayout).toBe("auto");
    await contains(".o-discuss-ChangeLayoutDialog-option.o-selected:contains('Auto (dynamic)')");
    // "Prioritize tiles with video" is only offered while the tiled layout is selected.
    await contains(".o-discuss-ChangeLayoutDialog input[type='checkbox'][role='switch']", {
        count: 0,
    });
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Tiled')");
    expect(store.settings.showOnlyVideo).toBe(false);
    await click(".o-discuss-ChangeLayoutDialog input[type='checkbox'][role='switch']");
    expect(store.settings.showOnlyVideo).toBe(true);
    // "Discuss" exits the fullscreen meeting view.
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Discuss')");
    await contains(".o-mail-Meeting", { count: 0 });
});
