import { Component, markup } from "@odoo/owl";
import { isMacOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { escape } from "@web/core/utils/strings";
import { session } from "@web/session";
import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";

function documentationItem(env) {
    const documentationURL = "https://www.odoo.com/documentation/18.0";
    return {
        type: "item",
        id: "documentation",
        description: _t("Documentation"),
        href: documentationURL,
        callback: () => {
            browser.open(documentationURL, "_blank");
        },
        sequence: 10,
    };
}

function supportItem(env) {
    const url = session.support_url;
    return {
        type: "item",
        id: "support",
        description: _t("Support"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

class ShortcutsFooterComponent extends Component {
    static template = "web.UserMenu.ShortcutsFooterComponent";
    static props = {};
    setup() {
        this.runShortcutKey = isMacOS() ? "CONTROL" : "ALT";
    }
}

function shortCutsItem(env) {
    // ℹ️ `_t` can only be inlined directly inside JS template literals after
    // Babel has been updated to version 2.12.
    const translatedText = _t("Shortcuts");
    return {
        type: "item",
        id: "shortcuts",
        hide: env.isSmall,
        description: markup(
            `<div class="d-flex align-items-center justify-content-between">
                <span>${escape(translatedText)}</span>
                <span class="fw-bold">${isMacOS() ? "CMD" : "CTRL"}+K</span>
            </div>`
        ),
        callback: () => {
            env.services.command.openMainPalette({ FooterComponent: ShortcutsFooterComponent });
        },
        sequence: 30,
    };
}

function separator() {
    return {
        type: "separator",
        sequence: 40,
    };
}

export function preferencesItem(env) {
    return {
        type: "item",
        id: "settings",
        description: _t("Preferences"),
        callback: async function () {
            const actionDescription = await env.services.orm.call("res.users", "action_get");
            actionDescription.res_id = user.userId;
            env.services.action.doAction(actionDescription);
        },
        sequence: 50,
    };
}

export function odooAccountItem(env) {
    return {
        type: "item",
        id: "account",
        description: _t("My Odoo.com account"),
        callback: () => {
            rpc("/web/session/account")
                .then((url) => {
                    browser.open(url, "_blank");
                })
                .catch(() => {
                    browser.open("https://accounts.odoo.com/account", "_blank");
                });
        },
        sequence: 60,
    };
}

function installPWAItem(env) {
    let description = _t("Install App");
    let callback = () => env.services.pwa.show();
    let show = () => env.services.pwa.isAvailable;
    const currentApp = env.services.menu.getCurrentApp();
    if (currentApp && ["barcode", "field-service", "shop-floor"].includes(currentApp.actionPath)) {
        // While the feature could work with all apps, we have decided to only
        // support the installation of the apps contained in this list
        // The list can grow in the future, by simply adding their path
        description = _t("Install %s", currentApp.name);
        callback = () => {
            window.open(
                `/scoped_app?app_id=${currentApp.webIcon.split(",")[0]}&path=${encodeURIComponent(
                    "scoped_app/" + currentApp.actionPath
                )}`
            );
        };
        show = () => !env.services.pwa.isScopedApp;
    }
    return {
        type: "item",
        id: "install_pwa",
        description,
        callback,
        show,
        sequence: 65,
    };
}

function logOutItem(env) {
    let route = "/web/session/logout";
    if (env.services.pwa.isScopedApp) {
        route += `?redirect=${encodeURIComponent(env.services.pwa.startUrl)}`;
    }
    return {
        type: "item",
        id: "logout",
        description: _t("Log out"),
        href: `${browser.location.origin}${route}`,
        callback: () => {
            browser.location.href = route;
        },
        sequence: 70,
    };
}

registry
    .category("user_menuitems")
    .add("documentation", documentationItem)
    .add("support", supportItem)
    .add("shortcuts", shortCutsItem)
    .add("separator", separator)
    .add("profile", preferencesItem)
    .add("odoo_account", odooAccountItem)
    .add("install_pwa", installPWAItem)
    .add("log_out", logOutItem);
