/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

export async function startClickEverywhere(xmlId, appsMenusOnly) {
    await loadBundle("web.assets_clickbot");
    window.clickEverywhere(xmlId, appsMenusOnly);
}

export function runClickTestItem({ env }) {
    return {
        type: "item",
        description: _t("Run Click Everywhere Test"),
        callback: () => {
            startClickEverywhere();
        },
        sequence: 30,
    };
}

export default {
    startClickEverywhere,
    runClickTestItem,
};

registry.category("debug").category("default").add("runClickTestItem", runClickTestItem);
