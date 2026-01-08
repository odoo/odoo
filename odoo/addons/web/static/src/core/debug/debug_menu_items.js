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
            await env.services.orm.call(
                "ir.attachment",
                "regenerate_assets_bundles",
            );
            browser.location.reload();
        },
        sequence: 430,
    };
}

export function becomeSuperuser({ env }) {
    const becomeSuperuserURL = browser.location.origin + "/web/become";
    if (!env.services.user.isAdmin) {
        return false;
    }
    return {
        type: "item",
        description: _t("Become Superuser"),
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
