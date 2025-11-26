import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    contains,
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
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

describe.current.tags("desktop");
defineMailModels();

test("message sound is 'off'", async () => {
    localStorage.setItem("mail.user_setting.message_sound", "false");
    await start();
    getService("action").doAction({
        tag: "mail.discuss_notification_settings_action",
        type: "ir.actions.client",
    });
    await contains("label:has(h5:contains('Message sound')) input:not(:checked)");
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
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains(".o-discuss-CallSettings");
    await contains(
        ".o-discuss-CallSettings-item:has(label:contains('Blur video background')) input:checked"
    );
    await contains(
        "label[title='Background blur intensity'] .o-discuss-DiscussCallSettings-width-text-percentage:text('10%')"
    );
    await contains(
        "label[title='Edge blur intensity'] .o-discuss-DiscussCallSettings-width-text-percentage:text('30%')"
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
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains(".o-discuss-CallSettings");
    await contains("input[title='Show video participants only']:checked");
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
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains(".o-discuss-CallSettings");
    await contains(".o-Discuss-CallSettings-thresholdInput:value(0.3)");
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
    await contains(".o-mail-Thread:contains('Welcome to #test')");
    await contains(".o-mail-ActionList-button[title='Members']");
    await contains(".o-mail-ActionList-button[title='Members']:not(.active)");
    const isMemberPanelOpenByDefaultKey = makeRecordFieldLocalId(
        DiscussApp.localId(),
        "isMemberPanelOpenByDefault"
    );
    expect(localStorage.getItem(isMemberPanelOpenByDefaultKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail.user_setting.no_members_default_open")).toBe(null);
    await click(".o-mail-ActionList-button[title='Members']");
    await contains(".o-mail-ActionList-button[title='Members'].active"); // just to validate .active is correct selector
    expect(localStorage.getItem(isMemberPanelOpenByDefaultKey)).toBe(null);
});

test("sidebar compact is 'on'", async () => {
    localStorage.setItem("mail.user_setting.discuss_sidebar_compact", "true");
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar.o-compact");
    const isSidebarCompact = makeRecordFieldLocalId(DiscussApp.localId(), "isSidebarCompact");
    expect(localStorage.getItem(isSidebarCompact)).toBe(toRawValue(true));
    expect(localStorage.getItem("mail.user_setting.discuss_sidebar_compact")).toBe(null);
});

test("category 'Channels' is folded", async () => {
    localStorage.setItem("discuss_sidebar_category_folded_channels", "true");
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Channels') .oi.oi-chevron-right");
    const channels_is_open = makeRecordFieldLocalId(
        DiscussAppCategory.localId("channels"),
        "is_open"
    );
    expect(localStorage.getItem(channels_is_open)).toBe(toRawValue(false));
    expect(localStorage.getItem("discuss_sidebar_category_folded_channels")).toBe(null);
});

test("category 'Direct messages' is folded", async () => {
    localStorage.setItem("discuss_sidebar_category_folded_chats", "true");
    await start();
    await openDiscuss();
    await contains(
        ".o-mail-DiscussSidebarCategory:contains('Direct messages') .oi.oi-chevron-right"
    );
    const chats_is_open = makeRecordFieldLocalId(DiscussAppCategory.localId("chats"), "is_open");
    expect(localStorage.getItem(chats_is_open)).toBe(toRawValue(false));
    expect(localStorage.getItem("discuss_sidebar_category_folded_chats")).toBe(null);
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
    await contains(".o-mail-Thread:contains('Welcome to #test')");
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
    await click("[title='Start Call']");
    await click("button[aria-label='Video Settings']");
    await click(".o-discuss-QuickVideoSettings button:has(:text('Advanced Settings'))");
    await contains("input[title='Auto-focus speaker']:not(:checked)");
    // correct local storage values
    const useCallAutoFocusKey = makeRecordFieldLocalId(Settings.localId(), "useCallAutoFocus");
    expect(localStorage.getItem(useCallAutoFocusKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail_user_setting_disable_call_auto_focus")).toBe(null);
});

test("device input/output id", async () => {
    patchWithCleanup(browser.navigator.mediaDevices, {
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
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    rtc.microphonePermission = "granted";
    rtc.cameraPermission = "granted";
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Call Settings')");
    await contains(".o-discuss-CallSettings");
    await contains(
        "label[title='Microphone'] .o-mail-DeviceSelect-button[data-kind='audioinput']:text('audio_input_2_label')"
    );
    await contains(
        "label[title='Speakers'] .o-mail-DeviceSelect-button[data-kind='audiooutput']:text('audio_output_2_label')"
    );
    await contains(
        "label[title='Camera'] .o-mail-DeviceSelect-button[data-kind='videoinput']:text('video_input_2_label')"
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
