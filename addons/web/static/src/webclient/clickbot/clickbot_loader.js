// @ts-check

/** @module @web/webclient/clickbot/clickbot_loader - Debug menu item that loads and runs the click-everywhere automated test bot */

/**
 * @param {string} [xmlId]
 * @param {boolean} [light]
 * @param {any} [currentState]
 */
import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
export async function startClickEverywhere(xmlId, light, currentState) {
    await loadBundle("web.assets_clickbot");
    /** @type {any} */ (window).clickEverywhere(xmlId, light, currentState);
}

export function runClickTestItem({ env }) {
    return {
        type: "item",
        description: _t("Run Click Everywhere"),
        callback: () => {
            startClickEverywhere();
        },
        sequence: 460,
        section: "testing",
    };
}

const currentState = JSON.parse(browser.localStorage.getItem("running.clickbot"));
if (currentState) {
    startClickEverywhere(currentState.xmlId, currentState.light, currentState);
}

export default {
    startClickEverywhere,
    runClickTestItem,
};

registry
    .category("debug")
    .category("default")
    .add("runClickTestItem", /** @type {any} */ (runClickTestItem));
