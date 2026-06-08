import { registry } from "@web/core/registry";

export function htmlEditorVersions() {
    return Object.keys(registry.category("html_editor_upgrade").subRegistries).sort(
        compareVersions
    );
}

export const VERSION_SELECTOR = "[data-oe-version]";

export function stripVersion(element) {
    element.querySelectorAll(VERSION_SELECTOR).forEach((el) => {
        delete el.dataset.oeVersion;
    });
}

/**
 * Compare 2 versions
 *
 * @param {string} version1
 * @param {string} version2
 * @returns {number} -1 if version1 < version2
 *                   0 if version1 === version2
 *                   1 if version1 > version2
 */
export function compareVersions(version1, version2) {
    version1 = version1.split(".").map((v) => parseInt(v));
    version2 = version2.split(".").map((v) => parseInt(v));
    if (version1[0] < version2[0] || (version1[0] === version2[0] && version1[1] < version2[1])) {
        return -1;
    } else if (version1[0] === version2[0] && version1[1] === version2[1]) {
        return 0;
    } else {
        return 1;
    }
}
