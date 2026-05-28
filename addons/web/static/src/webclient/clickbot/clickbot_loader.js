import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

export async function startClickEverywhere(xmlId, light, currentState) {
    await loadBundle("web.assets_clickbot");
    window.clickEverywhere(xmlId, light, currentState);
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
if (currentState && !currentState.done) {
    startClickEverywhere(currentState.xmlId, currentState.light, currentState);
} else if (currentState) {
    browser.localStorage.removeItem("running.clickbot");
}

export default {
    startClickEverywhere,
    runClickTestItem,
};

registry.category("debug").category("default").add("runClickTestItem", runClickTestItem);
