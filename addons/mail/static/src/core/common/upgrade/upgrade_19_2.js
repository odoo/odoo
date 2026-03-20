import { addUpgrade } from "@mail/core/common/upgrade/upgrade_helpers";

/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnParam} UpgradeFnParam */
/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnReturn} UpgradeFnReturn */

export const upgrade_19_2 = {
    /**
     * @param {string|(key: string) => string} key
     * @param {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
     * @returns {UpgradeFnReturn}
     */
    add(key, upgrade) {
        return addUpgrade({ key, version: "19.2", upgrade });
    },
    /**
     * Copy from parseRawValue at the time.
     * Dedicate function so that it never change in the future for these 19.2 scripts.
     *
     * @param {string} rawValue
     */
    parseRawValue(rawValue) {
        try {
            return JSON.parse(rawValue);
        } catch {
            return undefined;
        }
    },
};

upgrade_19_2.add("mail.user_setting.push_notification_dismissed", {
    key: "Store:isNotificationPermissionDismissed",
    value: true,
});

const settingsFields = [
    "messageSound",
    "useCallAutoFocus",
    "useBlur",
    "audioInputDeviceId",
    "audioOutputDeviceId",
    "cameraInputDeviceId",
    "backgroundBlurAmount",
    "edgeBlurAmount",
    "showOnlyVideo",
    "voiceActivationThreshold",
];

for (const fieldName of settingsFields) {
    upgrade_19_2.add(`Settings,undefined:${fieldName}`, ({ value }) => ({
        key: `Settings:${fieldName}`,
        value: upgrade_19_2.parseRawValue(value).value,
    }));
}
