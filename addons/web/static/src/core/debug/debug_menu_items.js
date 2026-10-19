import { _t } from "@web/core/l10n/translation";
import { location, browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { isRPCCacheDisabled } from "@web/core/network/rpc_cache";
import { usePlugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";

function activateTestsAssetsDebugging() {
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

export function regenerateAssets() {
    const orm = usePlugin(ORM);
    return {
        type: "item",
        description: _t("Regenerate Assets"),
        callback: async () => {
            await orm.call("ir.attachment", "regenerate_assets_bundles");
            location.reload();
        },
        sequence: 550,
        section: "tools",
    };
}

export function becomeSuperuser() {
    const becomeSuperuserURL = location.origin + "/web/become";
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

export function toggleRPCCache() {
    const disabled = isRPCCacheDisabled();
    return {
        type: "item",
        description: disabled ? _t("Enable RPC Cache") : _t("Disable RPC Cache"),
        callback: () => {
            // the cache is only instantiated at startup, so the webclient has to
            // be reloaded for the new value to be taken into account
            router.pushState({ cache: disabled ? undefined : 0 }, { reload: true });
        },
        sequence: 570,
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
    .add("toggleRPCCache", toggleRPCCache)
    .add("activateTestsAssetsDebugging", activateTestsAssetsDebugging)
    .add("leaveDebugMode", leaveDebugMode);
