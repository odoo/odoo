import { getCurrentLocalStorageVersion, LocalStorageEntry } from "@mail/utils/common/local_storage";
import { parseVersion } from "@mail/utils/common/misc";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} UpgradeData
 * @property {string} version
 * @property {string|RegExp} key
 * @property {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
 */
/**
 * @typedef {Object} UpgradeDataWithoutVersion
 * @property {string|RegExp} key
 * @property {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgrade
 */
/**
 * @typedef {Object} UpgradeFnParam
 * @property {string} key
 * @property {any} value
 * @property {ReturnType<typeof String.prototype.match>} [matchOfKey] Only when upgrade data has key as RegExp
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
        const allKeys = [];
        if (keyMap.values().some((i) => i.key instanceof RegExp)) {
            for (const i in localStorage) {
                // eslint-disable-next-line no-prototype-builtins
                if (localStorage.hasOwnProperty(i)) {
                    allKeys.push(i);
                }
            }
        }
        for (const upgradeData of keyMap.values()) {
            applyUpgrade(upgradeData, { allKeys });
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
 * @param {Object} [param1={}]
 * @param {string[]} [param1.allKeys] When upgrade to a given version has scripts with key as function,
 *   all the keys in local storage are provided in this param. This allows to read all local storage keys only once
 *   per upgrade step to a specific version.
 */
function applyUpgrade(upgradeData, { allKeys } = {}) {
    if (upgradeData.key instanceof RegExp) {
        allKeys
            .map((k) => k.match(upgradeData.key))
            .filter((matchOfKey) => matchOfKey)
            .forEach((matchOfKey) =>
                applyUpgradeOnKey(matchOfKey[0], upgradeData.upgrade, { matchOfKey })
            );
    } else {
        applyUpgradeOnKey(upgradeData.key, upgradeData.upgrade);
    }
}

/**
 * @param {string} oldKey
 * @type {((param: UpgradeFnParam) => UpgradeFnReturn)|UpgradeFnReturn} upgradeFn
 * @param {Object} [param2={}]
 * @param {ReturnType<typeof String.prototype.match>} [param2.matchOfKey]
 */
function applyUpgradeOnKey(oldKey, upgradeFn, { matchOfKey } = {}) {
    const oldEntry = new LocalStorageEntry(oldKey);
    const oldValue = oldEntry.rawGet() ?? oldEntry.get();
    if (oldValue === undefined) {
        return; // could not upgrade (cannot parse or more recent version)
    }
    const { key, value } =
        typeof upgradeFn === "function"
            ? upgradeFn({ key: oldKey, value: oldValue, matchOfKey })
            : upgradeFn;
    oldEntry.remove();
    const newEntry = new LocalStorageEntry(key);
    newEntry.set(value);
}
