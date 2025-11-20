import { addUpgrade } from "@mail/core/common/upgrade/upgrade_helpers";

/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnParam} UpgradeFnParam */
/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnReturn} UpgradeFnReturn */

export const upgrade_19_1 = {
    /**
     * @param {string} key
     * @param {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
     * @returns {UpgradeFnReturn}
     */
    add(key, upgrade) {
        return addUpgrade({ key, version: "19.1", upgrade });
    },
};

upgrade_19_1.add("mail.user_setting.message_sound", {
    key: "Settings,undefined:messageSound",
    value: false,
});

upgrade_19_1.add("mail_user_setting_disable_call_auto_focus", {
    key: "Settings,undefined:useCallAutoFocus",
    value: false,
});

upgrade_19_1.add("mail_user_setting_use_blur", {
    key: "Settings,undefined:useBlur",
    value: true,
});

upgrade_19_1.add("mail_user_setting_audio_input_device_id", ({ value }) => ({
    key: "Settings,undefined:audioInputDeviceId",
    value,
}));

upgrade_19_1.add("mail_user_setting_audio_output_device_id", ({ value }) => ({
    key: "Settings,undefined:audioOutputDeviceId",
    value,
}));

upgrade_19_1.add("mail_user_setting_camera_input_device_id", ({ value }) => ({
    key: "Settings,undefined:cameraInputDeviceId",
    value,
}));

upgrade_19_1.add("mail_user_setting_background_blur_amount", ({ value }) => ({
    key: "Settings,undefined:backgroundBlurAmount",
    value: parseInt(value),
}));

upgrade_19_1.add("mail_user_setting_edge_blur_amount", ({ value }) => ({
    key: "Settings,undefined:edgeBlurAmount",
    value: parseInt(value),
}));

upgrade_19_1.add("mail_user_setting_show_only_video", {
    key: "Settings,undefined:showOnlyVideo",
    value: true,
});

upgrade_19_1.add("mail_user_setting_voice_threshold", ({ value }) => ({
    key: "Settings,undefined:voiceActivationThreshold",
    value: parseFloat(value),
}));
