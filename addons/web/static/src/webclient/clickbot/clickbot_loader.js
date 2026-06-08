import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

async function _waitForEnv() {
    while (!odoo.__WOWL_DEBUG__?.root?.env) {
        await new Promise((resolve) => browser.setTimeout(resolve, 50));
    }
    return odoo.__WOWL_DEBUG__.root.env;
}

export async function startClickEverywhere(xmlId, light, currentState) {
    await loadBundle("web.assets_clickbot");
    const { Clickbot } = odoo.loader.modules.get("@web/webclient/clickbot/clickbot");
    const env = await _waitForEnv();
    return new Clickbot(env, { xmlId, light, currentState }).start();
}

export function runClickTestItem() {
    return {
        type: "item",
        description: _t("Run Click Everywhere"),
        callback: () => startClickEverywhere(),
        sequence: 460,
        section: "testing",
    };
}

const currentState = JSON.parse(browser.localStorage.getItem("running.clickbot"));
if (currentState) {
    startClickEverywhere(currentState.xmlId, currentState.light, currentState);
}

registry.category("debug").category("default").add("runClickTestItem", runClickTestItem);
