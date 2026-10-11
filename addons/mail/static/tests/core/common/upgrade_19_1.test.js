import { describe, expect, test, waitFor } from "@odoo/hoot";
import {
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { Settings } from "@mail/core/common/settings_model";
import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { contains, getService, serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

test("message sound is 'off'", async () => {
    localStorage.setItem("mail.user_setting.message_sound", "false");
    await start();
    expect(serverState.serverVersion).toEqual([99, 9]);
    getService("action").doAction({
        tag: "mail.discuss_notification_settings_action",
        type: "ir.actions.client",
    });
    await waitFor("label:has(h5:contains('Message sound')) input:not(:checked):count(1)");
    const messageSoundKey = makeRecordFieldLocalId(Settings.localId(), "messageSound");
    expect(localStorage.getItem(messageSoundKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail.user_setting.message_sound")).toBe(null);
});

test("message sound is 'off' (serverVersion with 'saas~' prefix)", async () => {
    // same test as above but testing with server version with `saas~` prefix that should be ignored and upgrade as expected.
    localStorage.setItem("mail.user_setting.message_sound", "false");
    await start({ serverVersion: ["saas~99", "9"] });
    expect(serverState.serverVersion).toEqual(["saas~99", "9"]);
    getService("action").doAction({
        tag: "mail.discuss_notification_settings_action",
        type: "ir.actions.client",
    });
    await waitFor("label:has(h5:contains('Message sound')) input:not(:checked):count(1)");
    const messageSoundKey = makeRecordFieldLocalId(Settings.localId(), "messageSound");
    expect(localStorage.getItem(messageSoundKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail.user_setting.message_sound")).toBe(null);
});

test("use blur is 'on'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail_user_setting_use_blur", "true");
    localStorage.setItem("mail_user_setting_background_blur_amount", "2"); // range from 0-20, to percentage. 2 => 10%
    localStorage.setItem("mail_user_setting_edge_blur_amount", "6"); // range from 0-20, to percentage. 6 => 30%
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Voice & Video Settings'):count(1)").click();
    await waitFor(".o-discuss-CallSettings:count(1)");
    await contains("button[title='Video']:count(1)").click();
    await waitFor("input[title='Blur video background']:checked:count(1)");
    await waitFor(
        "div[title='Background blur intensity'] .o-discuss-DiscussCallSettings-width-text-percentage:text('10%'):count(1)"
    );
    await waitFor(
        "div[title='Edge blur intensity'] .o-discuss-DiscussCallSettings-width-text-percentage:text('30%'):count(1)"
    );
    const useBlurKey = makeRecordFieldLocalId(Settings.localId(), "useBlur");
    expect(localStorage.getItem(useBlurKey)).toBe(toRawValue(true));
    const backgroundBlurAmountKey = makeRecordFieldLocalId(
        Settings.localId(),
        "backgroundBlurAmount"
    );
    expect(localStorage.getItem(backgroundBlurAmountKey)).toBe(toRawValue(2));
    const edgeBlurAmountKey = makeRecordFieldLocalId(Settings.localId(), "edgeBlurAmount");
    expect(localStorage.getItem(edgeBlurAmountKey)).toBe(toRawValue(6));
    expect(localStorage.getItem("mail_user_setting_use_blur")).toBe(null);
    expect(localStorage.getItem("mail_user_setting_background_blur_amount")).toBe(null);
    expect(localStorage.getItem("mail_user_setting_edge_blur_amount")).toBe(null);
});

test("show only video 'on'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail_user_setting_show_only_video", "true");
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    expect(getService("mail.store").settings.showOnlyVideo).toBe(true);
    const showOnlyVideoKey = makeRecordFieldLocalId(Settings.localId(), "showOnlyVideo");
    expect(localStorage.getItem(showOnlyVideoKey)).toBe(toRawValue(true));
    expect(localStorage.getItem("mail_user_setting_show_only_video")).toBe(null);
});

test("voice activation threshold", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail_user_setting_voice_threshold", "0.3");
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Voice & Video Settings'):count(1)").click();
    await waitFor(".o-discuss-CallSettings:count(1)");
    await waitFor(".o-Discuss-CallSettings-thresholdInput:value(0.3):count(1)");
    const voiceActivationThresholdKey = makeRecordFieldLocalId(
        Settings.localId(),
        "voiceActivationThreshold"
    );
    expect(localStorage.getItem(voiceActivationThresholdKey)).toBe(toRawValue(0.3));
    expect(localStorage.getItem("mail_user_setting_voice_threshold")).toBe(null);
});

test("member default open is 'off'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail.user_setting.no_members_default_open", "true");
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Thread:contains('Welcome to #test'):count(1)");
    await waitFor(".o-mail-ActionList-button[title='Members']:count(1)");
    await waitFor(".o-mail-ActionList-button[title='Members']:not(.active):count(1)");
    const isMemberPanelOpenByDefaultKey = makeRecordFieldLocalId(
        DiscussApp.localId(),
        "isMemberPanelOpenByDefault"
    );
    expect(localStorage.getItem(isMemberPanelOpenByDefaultKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail.user_setting.no_members_default_open")).toBe(null);
    await contains(".o-mail-ActionList-button[title='Members']:count(1)").click();
    await waitFor(".o-mail-ActionList-button[title='Members'].active:count(1)"); // just to validate .active is correct selector
    expect(localStorage.getItem(isMemberPanelOpenByDefaultKey)).toBe(null);
});

test("last active id of discuss app", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem(
        "mail.user_setting.discuss_last_active_id",
        `discuss.channel_${channelId}`
    );
    await start();
    await openDiscuss();
    await waitFor(".o-mail-Thread:contains('Welcome to #test'):count(1)");
    const lastActiveId = makeRecordFieldLocalId(DiscussApp.localId(), "lastActiveId");
    expect(localStorage.getItem(lastActiveId)).toBe(toRawValue(`discuss.channel_${channelId}`));
    expect(localStorage.getItem("mail.user_setting.discuss_last_active_id")).toBe(null);
});

test("call auto focus is 'off", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail_user_setting_disable_call_auto_focus", "true");
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await contains("button[aria-label='Video Settings']:count(1)").click();
    await contains(
        ".o-discuss-QuickVideoSettings button:has(:text('Advanced Settings')):count(1)"
    ).click();
    await waitFor(
        ".o-discuss-CallSettings .o-mail-TabHeader.o-active:has(:text('Video')):count(1)"
    );
    await waitFor("input[title='Auto-focus speaker']:not(:checked):count(1)");
    // correct local storage values
    const useCallAutoFocusKey = makeRecordFieldLocalId(Settings.localId(), "useCallAutoFocus");
    expect(localStorage.getItem(useCallAutoFocusKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail_user_setting_disable_call_auto_focus")).toBe(null);
});

test("device input/output id", async () => {
    patch(window.navigator.mediaDevices, {
        enumerateDevices: () =>
            Promise.resolve([
                {
                    deviceId: "audio_input_1_id",
                    kind: "audioinput",
                    label: "audio_input_1_label",
                },
                {
                    deviceId: "audio_input_2_id",
                    kind: "audioinput",
                    label: "audio_input_2_label",
                },
                {
                    deviceId: "audio_input_3_id",
                    kind: "audioinput",
                    label: "audio_input_3_label",
                },
                {
                    deviceId: "audio_output_1_id",
                    kind: "audiooutput",
                    label: "audio_output_1_label",
                },
                {
                    deviceId: "audio_output_2_id",
                    kind: "audiooutput",
                    label: "audio_output_2_label",
                },
                {
                    deviceId: "audio_output_3_id",
                    kind: "audiooutput",
                    label: "audio_output_3_label",
                },
                {
                    deviceId: "video_input_1_id",
                    kind: "videoinput",
                    label: "video_input_1_label",
                },
                {
                    deviceId: "video_input_2_id",
                    kind: "videoinput",
                    label: "video_input_2_label",
                },
                {
                    deviceId: "video_input_3_id",
                    kind: "videoinput",
                    label: "video_input_3_label",
                },
            ]),
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    localStorage.setItem("mail_user_setting_audio_input_device_id", "audio_input_2_id");
    localStorage.setItem("mail_user_setting_audio_output_device_id", "audio_output_2_id");
    localStorage.setItem("mail_user_setting_camera_input_device_id", "video_input_2_id");
    await start();
    const rtc = getService("discuss.rtc");
    rtc.microphonePermission = "granted";
    rtc.cameraPermission = "granted";
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Voice & Video Settings'):count(1)").click();
    await waitFor(".o-discuss-CallSettings:count(1)");
    await waitFor(
        "div[aria-label='Microphone'] .o-mail-DeviceSelect-button[data-kind='audioinput']:text('audio_input_2_label'):count(1)"
    );
    await waitFor(
        "div[aria-label='Speakers'] .o-mail-DeviceSelect-button[data-kind='audiooutput']:text('audio_output_2_label'):count(1)"
    );
    await contains("button[title='Video']:count(1)").click();
    await waitFor(
        "div[aria-label='Camera'] .o-mail-DeviceSelect-button[data-kind='videoinput']:text('video_input_2_label'):count(1)"
    );
    // correct local storage values
    const audioInputDeviceIdKey = makeRecordFieldLocalId(Settings.localId(), "audioInputDeviceId");
    expect(localStorage.getItem(audioInputDeviceIdKey)).toBe(toRawValue("audio_input_2_id"));
    const audioOutputDeviceIdKey = makeRecordFieldLocalId(
        Settings.localId(),
        "audioOutputDeviceId"
    );
    expect(localStorage.getItem(audioOutputDeviceIdKey)).toBe(toRawValue("audio_output_2_id"));
    const videoInputDeviceIdKey = makeRecordFieldLocalId(Settings.localId(), "cameraInputDeviceId");
    expect(localStorage.getItem(videoInputDeviceIdKey)).toBe(toRawValue("video_input_2_id"));
    expect(localStorage.getItem("mail_user_setting_audio_input_device_id")).toBe(null);
    expect(localStorage.getItem("mail_user_setting_audio_output_device_id")).toBe(null);
    expect(localStorage.getItem("mail_user_setting_camera_input_device_id")).toBe(null);
});
