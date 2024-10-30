import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

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

export function becomeSuperuser({ env }) {
    const becomeSuperuserURL = browser.location.origin + "/web/become";
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
    .add("regenerateAssets", regenerateAssets)
    .add("becomeSuperuser", becomeSuperuser)
    .add("activateTestsAssetsDebugging", activateTestsAssetsDebugging)
    .add("leaveDebugMode", leaveDebugMode);
