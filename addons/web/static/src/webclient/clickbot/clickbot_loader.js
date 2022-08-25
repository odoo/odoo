/** @odoo-module alias=web.clickEverywhere **/

import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";

export default async function startClickEverywhere(xmlId, appsMenusOnly) {
    await loadJS("web/static/src/webclient/clickbot/clickbot.js");
    window.clickEverywhere(xmlId, appsMenusOnly);
}

function runClickTestItem({ env }) {
    return {
        type: "item",
        description: env._t("Run Click Everywhere Test"),
        callback: () => {
            startClickEverywhere();
        },
        sequence: 30,
    };
}

registry.category("debug").category("default").add("runClickTestItem", runClickTestItem);
