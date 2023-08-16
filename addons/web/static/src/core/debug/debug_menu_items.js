/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { routeToUrl } from "@web/core/browser/router_service";
import { registry } from "@web/core/registry";

function activateAssetsDebugging({ env }) {
    return {
        type: "item",
        description: _t("Activate Assets Debugging"),
        callback: () => {
            browser.location.search = "?debug=assets";
        },
        sequence: 410,
    };
}

function activateTestsAssetsDebugging({ env }) {
    return {
        type: "item",
        description: _t("Activate Tests Assets Debugging"),
        callback: () => {
            browser.location.search = "?debug=assets,tests";
        },
        sequence: 420,
    };
}

export function regenerateAssets({ env }) {
    return {
        type: "item",
        description: _t("Regenerate Assets Bundles"),
        callback: async () => {
            const domain = [
                "&",
                ["res_model", "=", "ir.ui.view"],
                "|",
                ["name", "=like", "%.assets_%.css"],
                ["name", "=like", "%.assets_%.js"],
            ];
            const ids = await env.services.orm.search("ir.attachment", domain);
            await env.services.orm.unlink("ir.attachment", ids);
            browser.location.reload();
        },
        sequence: 430,
    };
}

function becomeSuperuser({ env }) {
    const becomeSuperuserURL = browser.location.origin + "/web/become";
    return {
        type: "item",
        description: _t("Become Superuser"),
        hide: !env.services.user.isAdmin,
        href: becomeSuperuserURL,
        callback: () => {
            browser.open(becomeSuperuserURL, "_self");
        },
        sequence: 440,
    };
}

function leaveDebugMode({ env }) {
    return {
        type: "item",
        description: _t("Leave the Developer Tools"),
        callback: () => {
            const route = env.services.router.current;
            route.search.debug = "";
            browser.location.href = browser.location.origin + routeToUrl(route);
        },
        sequence: 450,
    };
}

registry
    .category("debug")
    .category("default")
    .add("activateAssetsDebugging", activateAssetsDebugging)
    .add("regenerateAssets", regenerateAssets)
    .add("becomeSuperuser", becomeSuperuser)
    .add("leaveDebugMode", leaveDebugMode)
    .add("activateTestsAssetsDebugging", activateTestsAssetsDebugging);
