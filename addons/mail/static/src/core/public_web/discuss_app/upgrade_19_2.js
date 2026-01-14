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
};

upgrade_19_2.add(/^mail\.sidebar_category_(.*)_hidden$/, ({ matchOfKey }) => ({
    key: `DiscussAppCategory,${matchOfKey[1]}:hidden`,
    value: true,
}));
