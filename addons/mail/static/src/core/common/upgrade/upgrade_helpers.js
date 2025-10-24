import { getCurrentLocalStorageVersion, LocalStorageEntry } from "@mail/utils/common/local_storage";
import { parseVersion } from "@mail/utils/common/misc";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} UpgradeData
 * @property {string} version
 * @property {string} key
 * @property {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
 */
/**
 * @typedef {Object} UpgradeDataWithoutVersion
 * @property {string} key
 * @property {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
 */
/**
 * @typedef {Object} UpgradeFnParam
 * @property {string} key
 * @property {any} value
 */
/**
 * @typedef {Object} UpgradeFnReturn
 * @property {string} key
 * @property {any} value
 */

/**
 * Register a `key` and `upgrade` function for a `version` of local storage.
 *
 * When there's request to upgrade a local storage
 *
 * Example:
 * - we have versions 19.1, 19.3, and 20.0.
 * - define upgrade function with 19.1 is to upgrade to 19.1
 * - define ugrade function with 20.0 is to upgrade to 20.0
 *
 * Upgrades are applied in sequence, i.e.:
 * - if version is 20.0 and local storage data are in version 0, this will apply upgrade to 19.1, then to 19.3 and finally to 20.0.
 * - if version is 20.0 and local storage data are in version 19.1, this will apply upgrade to 19.3 and finally to 20.0.
 * - if version is 20.0 and local storage data are in version 19.2, this will apply upgrade to 19.3 and finally to 20.0.
 * - if version is 20.0 and local storage data are in version 20.0, this will not upgrade data.
 *
 * @param {UpgradeData} param0
 */
export function addUpgrade({ version, key, upgrade }) {
    /** @type {Map<string, Function[]>} */
    const map = getUpgradeMap();
    if (!map.has(version)) {
        map.set(version, new Map());
    }
    map.get(version).set(key, { version, key, upgrade });
}

/** @param {string} version */
export function upgradeFrom(version) {
    const orderedUpgradeList = Array.from(getUpgradeMap().entries())
        .filter(
            ([v]) =>
                !parseVersion(v).isLowerThan(version) &&
                !parseVersion(getCurrentLocalStorageVersion()).isLowerThan(v)
        )
        .sort(([v1], [v2]) => (parseVersion(v1).isLowerThan(v2) ? -1 : 1));
    for (const [, keyMap] of orderedUpgradeList) {
        for (const upgradeData of keyMap.values()) {
            applyUpgrade(upgradeData);
        }
    }
}

const upgradeRegistry = registry.category("discuss.upgrade");
upgradeRegistry.add(null, new Map());

/**
 * A Map of version numbers to a Map of keys and upgrade functions.
 * Basically:
 *
 * Map: {
 *     "19.1": {
 *         key_1: upgradeData_1,
 *         key_2: upgradeData_2,
 *     },
 *     "19.2": {
 *         key_3: upgradeData_3,
 *         key_4: upgradeData_4,
 *         ...
 *     },
 *     ...
 * }
 *
 * To upgrade a key in a given version, find the key in version
 * and applyUpgrade using upgradeData to upgrade with new key, value and version.
 *
 * @return {Map<string, Map<string, UpgradeData>>}
 */
function getUpgradeMap() {
    return upgradeRegistry.get(null);
}

/**
 * Upgrade local storage using `upgrade` data.
 * i.e. call `upgradeData.upgrade` to get new key and value.
 *
 * @param {UpgradeData} upgradeData
 */
function applyUpgrade(upgradeData) {
    const oldEntry = new LocalStorageEntry(upgradeData.key);
    const oldValue = oldEntry.rawGet() ?? oldEntry.get();
    if (oldValue === undefined) {
        return; // could not upgrade (cannot parse or more recent version)
    }
    const { key, value } =
        typeof upgradeData.upgrade === "function"
            ? upgradeData.upgrade({ key: upgradeData.key, value: oldValue })
            : upgradeData.upgrade;
    oldEntry.remove();
    const newEntry = new LocalStorageEntry(key);
    newEntry.set(value);
}
