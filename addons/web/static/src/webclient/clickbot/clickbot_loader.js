import { Plugin, usePlugin, useScope } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { browser } from "@web/core/browser/browser";

let rootScope;

export async function startClickEverywhere(options) {
    await loadBundle("web.assets_clickbot");
    const { ClickbotLauncher } = odoo.loader.modules.get("@web/webclient/clickbot/clickbot");

    const launcher = rootScope.run(() => usePlugin(ClickbotLauncher));
    launcher.configure(options.currentState || options);
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

// Gives the scope needed to start the `ClickbotLauncher` plugin, which lives in a lazy bundle,
// to `startClickEverywhere`, and resumes a run interrupted by a page reload.
class ClickbotResumePlugin extends Plugin {
    setup() {
        rootScope = useScope();
        const currentState = browser.localStorage.getItem("running.clickbot");
        if (currentState) {
            startClickEverywhere({ withOverlay: true, currentState: JSON.parse(currentState) });
        }
    }
}
services.add(ClickbotResumePlugin);

registry
    .category("debug")
    .category("default")
    .add("runClickbotLauncherItem", runClickbotLauncherItem);
