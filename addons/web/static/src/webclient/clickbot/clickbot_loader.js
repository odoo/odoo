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

export async function startClickEverywhere(options) {
    await loadBundle("web.assets_clickbot");
    const { ClickbotLauncher } = odoo.loader.modules.get("@web/webclient/clickbot/clickbot");
    const env = await _waitForEnv();

    const launcher = new ClickbotLauncher(env, options.currentState || options);
    if (options.withOverlay) {
        launcher.open();
        return;
    }

    return launcher.start();
}

export function runClickbotLauncherItem() {
    return {
        type: "item",
        description: _t("Run ClickBot…"),
        callback: () => startClickEverywhere({ withOverlay: true }),
        sequence: 460,
        section: "testing",
    };
}

const currentState = JSON.parse(browser.localStorage.getItem("running.clickbot"));
if (currentState) {
    startClickEverywhere({ withOverlay: true, currentState });
}

registry
    .category("debug")
    .category("default")
    .add("runClickbotLauncherItem", runClickbotLauncherItem);
