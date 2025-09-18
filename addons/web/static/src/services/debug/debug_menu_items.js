// @ts-check

/**
 * Debug menu item factories for the default debug category.
 * Each factory receives `{ env }` and returns a debug menu item descriptor or false.
 *
 * @module @web/services/debug/debug_menu_items
 */

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/services/user";

/**
 * @typedef {Object} DebugMenuItemDescriptor
 * @property {"item"} type
 * @property {string} description - display label in the debug menu
 * @property {() => void | Promise<void>} callback
 * @property {string} [href] - optional link URL
 * @property {number} [sequence] - ordering within the section
 * @property {string} [section] - section grouping key
 */

/**
 * Activate the tests+assets debug mode.
 * @param {{ env: import("@web/env").OdooEnv }} params
 * @returns {DebugMenuItemDescriptor | void}
 */
function activateTestsAssetsDebugging({ env }) {
    if (String(router.current.debug).includes("tests")) {
        return;
    }

    return {
        type: "item",
        description: _t("Activate Test Mode"),
        callback: () => {
            router.pushState({ debug: "assets,tests" }, { reload: true });
        },
        sequence: 580,
        section: "tools",
    };
}

/**
 * Regenerate all asset bundles and reload the page.
 * @param {{ env: import("@web/env").OdooEnv }} params
 * @returns {DebugMenuItemDescriptor}
 */
export function regenerateAssets({ env }) {
    return {
        type: "item",
        description: _t("Regenerate Assets"),
        callback: async () => {
            await env.services.orm.call("ir.attachment", "regenerate_assets_bundles");
            browser.location.reload();
        },
        sequence: 550,
        section: "tools",
    };
}

/**
 * Navigate to the superuser endpoint. Only visible to admin users.
 * @param {{ env: import("@web/env").OdooEnv }} params
 * @returns {DebugMenuItemDescriptor | false}
 */
export function becomeSuperuser({ env }) {
    const becomeSuperuserURL = `${browser.location.origin}/web/become`;
    if (!user.isAdmin) {
        return false;
    }
    return {
        type: "item",
        description: _t("Become Superuser"),
        href: becomeSuperuserURL,
        callback: () => {
            browser.open(becomeSuperuserURL, "_self");
        },
        sequence: 560,
        section: "tools",
    };
}

/**
 * Leave debug mode by resetting the debug URL parameter.
 * @returns {DebugMenuItemDescriptor}
 */
function leaveDebugMode() {
    return {
        type: "item",
        description: _t("Leave Debug Mode"),
        callback: () => {
            router.pushState({ debug: 0 }, { reload: true });
        },
        sequence: 650,
    };
}

registry
    .category("debug")
    .category("default")
    .add("regenerateAssets", /** @type {any} */ (regenerateAssets))
    .add("becomeSuperuser", /** @type {any} */ (becomeSuperuser))
    .add(
        "activateTestsAssetsDebugging",
        /** @type {any} */ (activateTestsAssetsDebugging),
    )
    .add("leaveDebugMode", /** @type {any} */ (leaveDebugMode));
