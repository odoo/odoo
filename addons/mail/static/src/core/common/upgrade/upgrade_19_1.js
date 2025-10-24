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
