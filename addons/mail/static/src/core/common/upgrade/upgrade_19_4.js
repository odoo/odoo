import { addUpgrade } from "@mail/core/common/upgrade/upgrade_helpers";
import { isMobileOS } from "@web/core/browser/feature_detection";

/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnParam} UpgradeFnParam */
/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnReturn} UpgradeFnReturn */

export const upgrade_19_4 = {
    /**
     * @param {string} key
     * @param {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
     * @returns {UpgradeFnReturn}
     */
    add(key, upgrade) {
        return addUpgrade({ key, version: "19.4.0", upgrade });
    },
};

upgrade_19_4.add("mail.user_setting.chathub_compact", () => ({
    key: "ChatHub:compact",
    value: true,
}));

upgrade_19_4.add("Settings:usePushToTalk", () => ({
    key: "Settings:usePushToTalk",
    value: !isMobileOS(),
}));
