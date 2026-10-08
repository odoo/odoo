import {
    click,
    contains as mailContains,
    defineMailModels,
    editInput,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { CallSettings } from "@mail/discuss/call/common/call_settings";
import { parseRawValue, toRawValue } from "@mail/utils/common/local_storage";
import { Settings } from "@mail/core/common/settings_model";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { describe, expect, keyDown, mockDate, test, waitFor, waitForNone } from "@odoo/hoot";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import { isBrowserChrome } from "@web/core/browser/feature_detection";

describe.current.tags("desktop");
defineMailModels();

test("Device selectors match a selected device by ID and kind", async () => {
    patch(window.navigator.mediaDevices, {
        enumerateDevices: async () => [
            {
                deviceId: "default",
                kind: "audioinput",
                label: "Default headset microphone",
            },
            {
                deviceId: "default",
                kind: "audiooutput",
                label: "Default headset speakers",
            },
        ],
    });
    const env = await start();
    const store = env.services["mail.store"];
    store.settings.audioInputDeviceId = "default";
    store.settings.audioOutputDeviceId = "default";
    store.rtc.microphonePermission = "granted";

    await mountWithCleanup(CallSettings, {
        env,
        props: { withActionPanel: false },
    });

    // Browsers can use the same "default" device ID for the input and output
    // endpoints. When settings are reopened, the selected label must therefore
    // also be matched by kind, or the speaker selector displays the microphone
    // endpoint listed first by enumerateDevices().
    await mailContains(".o-mail-DeviceSelect-button[data-kind='audioinput']", {
        text: "Default headset microphone",
    });
    await mailContains(".o-mail-DeviceSelect-button[data-kind='audiooutput']", {
        text: "Default headset speakers",
    });
});

test("Renders the call settings", async () => {
    patch(window.navigator.mediaDevices, {
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
    await start();
    const rtc = getService("discuss.rtc");
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await waitFor(".o-discuss-CallSettings:count(1)");
    await waitFor("div[aria-label='Microphone']:count(1)");
    await waitFor("div[aria-label='Speakers']:count(1)");
    await waitFor(".o-mail-DeviceSelect-button:has(:text('Click to activate')):count(2)");
    rtc.microphonePermission = "granted";
    const browserDefaultLabel = isBrowserChrome() ? "Default" : "Browser Default";
    await click(".o-mail-DeviceSelect-button[data-kind='audioinput']:has(:text('Default'))");
    await waitFor(".o-dropdown-item:text('mockAudioDeviceLabel'):count(1)");
    await waitFor(`.o-dropdown-item:text(${browserDefaultLabel}):count(1)`);
    await waitFor("label[aria-label='Enable Push-to-talk']:count(1)");
    await waitFor("input[title='Voice detection sensitivity']:count(1)");
    await waitFor(".o-discuss-CallSettings button:text('Test'):count(1)");
    await click("button[title='Video']");
    await waitFor("div[aria-label='Camera']:count(1)");
    await waitFor(".o-mail-DeviceSelect-button:has(:text('Click to activate')):count(1)");
    rtc.cameraPermission = "granted";
    await click(".o-mail-DeviceSelect-button[data-kind='videoinput']:has(:text('Default'))");
    await waitFor(".o-dropdown-item:text('mockVideoDeviceLabel'):count(1)");
    await waitFor(`.o-dropdown-item:text(${browserDefaultLabel}):count(1)`);
    await waitFor("label span:text('Auto-focus speaker'):count(1)");
    await waitFor("label span:text('Blur video background'):count(1)");
});

test("activate push to talk", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await waitFor("input[title='Voice detection sensitivity']:count(1)");
    await click("label[aria-label='Enable Push-to-talk']");
    await waitFor("input[title='Delay after releasing push-to-talk']:count(1)");
    await waitForNone("input[title='Voice detection sensitivity']");
    // ensure push to talk settings updates reflect in UI
    await click("button[aria-label='Register new shortcut']");
    await keyDown("Ctrl+m");
    await waitFor("button[aria-label='Register new shortcut']:text('Ctrl+m'):count(1)");
    await waitFor(".o-discuss-CallSettings-voiceActiveDuration:text('200ms'):count(1)");
    await editInput(document.body, ".o-discuss-CallSettings-delayInput", 560);
    await waitFor(".o-discuss-CallSettings-voiceActiveDuration:text('560ms'):count(1)");
});

test("activate blur", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await click("button[title='Video']");
    await click("input[title='Blur video background']");
    await waitFor("div[title='Background blur intensity'] span:has(:text('Intensity')):count(1)");
    await waitFor("div[title='Edge blur intensity'] span:has(:text('Edge Softness')):count(1)");
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
    patch(localStorage, {
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
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await waitFor("label[aria-label='Enable Push-to-talk']:count(1)");
    await editInput(document.body, "input[title='Voice detection sensitivity']", 0.3);
    await expect.waitForSteps([`${voiceActivationThresholdKey}: 0.3`]);
    await click("button[title='Video']");
    await waitFor("input[title='Blur video background']:checked:count(1)");
    await waitFor("div[title='Background blur intensity']:has(:text('15%')):count(1)");
    await waitFor("div[title='Edge blur intensity']:has(:text('25%')):count(1)");
    await click("input[title='Blur video background']");
    expect(localStorage.getItem(useBlurLocalStorageKey)).toBe(null);
});

test("Adjust view dialog: each layout option and the prioritize-video toggle persist the setting", async () => {
    mockGetMedia();
    mockDate("2026-01-01 10:00:00");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    const store = getService("mail.store");
    await openDiscuss(channelId);
    await click(".o-mail-MessagingMenu-tab[data-id='meeting']");
    await click("button:text('Meeting')");
    await click(".o-dropdown-item:text('Start Now')");
    await waitFor(".o-mail-Meeting:count(1)");
    await click(".o-discuss-CallActionList button[title='More']");
    await click("[name='change-layout']");
    await waitFor(".o-discuss-ChangeLayoutDialog:count(1)");
    await waitFor(".o-discuss-ChangeLayoutDialog-option:count(5)");
    // Each grid layout is persisted and reflected as the selected row.
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Tiled')");
    expect(store.settings.callLayout).toBe("tiled");
    await waitFor(".o-discuss-ChangeLayoutDialog-option.o-selected:contains('Tiled'):count(1)");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Spotlight')");
    expect(store.settings.callLayout).toBe("spotlight");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Sidebar')");
    expect(store.settings.callLayout).toBe("sidebar");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Auto (dynamic)')");
    expect(store.settings.callLayout).toBe("auto");
    await waitFor(
        ".o-discuss-ChangeLayoutDialog-option.o-selected:contains('Auto (dynamic)'):count(1)"
    );
    // "Prioritize tiles with video" is only offered while the tiled layout is selected.
    await waitForNone(".o-discuss-ChangeLayoutDialog input[type='checkbox'][role='switch']");
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Tiled')");
    expect(store.settings.showOnlyVideo).toBe(false);
    await click(".o-discuss-ChangeLayoutDialog input[type='checkbox'][role='switch']");
    expect(store.settings.showOnlyVideo).toBe(true);
    // "Discuss" exits the fullscreen meeting view.
    await click(".o-discuss-ChangeLayoutDialog-option:contains('Discuss')");
    await waitForNone(".o-mail-Meeting");
});

test("Changing inputs in Call Settings should pre-ask for browser permission", async () => {
    patch(window.navigator.mediaDevices, {
        enumerateDevices: () =>
            Promise.resolve([
                {
                    deviceId: "mockAudioDeviceId1",
                    kind: "audioinput",
                    label: "mockAudioDeviceLabel1",
                },
                {
                    deviceId: "mockAudioDeviceId2",
                    kind: "audioinput",
                    label: "mockAudioDeviceLabel2",
                },
            ]),
        getUserMedia: async (...args) => {
            expect.step("getUserMedia:permission-asked");
            expect.step(JSON.stringify(args));
            return { getTracks: () => [] };
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    getService("discuss.rtc").microphonePermission = "granted";
    await openDiscuss(channelId);
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await waitFor(".o-discuss-CallSettings:count(1)");
    await click(".o-mail-DeviceSelect-button[data-kind='audioinput']");
    await click(".o-dropdown-item:text('mockAudioDeviceLabel2')");
    await waitFor(
        ".o-mail-DeviceSelect-button[data-kind='audioinput']:text('mockAudioDeviceLabel2'):count(1)"
    );
    await expect.waitForSteps([
        "getUserMedia:permission-asked",
        '[{"audio":{"echoCancellation":true,"noiseSuppression":true,"deviceId":"mockAudioDeviceId2"},"video":false}]',
    ]);
});
