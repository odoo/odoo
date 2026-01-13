import { addUpgrade } from "@mail/core/common/upgrade/upgrade_helpers";

/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnParam} UpgradeFnParam */
/** @typedef {import("@mail/core/common/upgrade/upgrade_helpers").UpgradeFnReturn} UpgradeFnReturn */

export const upgrade_19_2 = {
    /**
     * @param {string} key
     * @param {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
     * @returns {UpgradeFnReturn}
     */
    add(key, upgrade) {
        return addUpgrade({ key, version: "19.2", upgrade });
    },
};

upgrade_19_2.add("mail.user_setting.push_notification_dismissed", {
    key: "Store,undefined:isNotificationPermissionDismissed",
    value: true,
});
