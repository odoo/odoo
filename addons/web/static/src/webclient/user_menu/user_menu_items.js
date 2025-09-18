// @ts-check

/** @module @web/webclient/user_menu/user_menu_items - User menu item factories registered in user_menuitems registry (help, shortcuts, preferences, PWA install, log out) */

import { Component, markup } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isMacOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/services/user";
import { session } from "@web/session";

/**
 * User menu item factory: "Help" link to support URL.
 * @param {Object} env
 * @returns {Object} menu item descriptor
 */
function supportItem(env) {
    const url = session.support_url;
    return {
        type: "item",
        id: "support",
        description: _t("Help"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

class ShortcutsFooterComponent extends Component {
    static template = "web.UserMenu.ShortcutsFooterComponent";
    static props = {
        switchNamespace: { type: Function, optional: true },
    };
    setup() {
        this.runShortcutKey = isMacOS() ? "CONTROL" : "ALT";
    }
}

/**
 * User menu item factory: keyboard shortcuts launcher (CMD/CTRL+K).
 * @param {Object} env
 * @returns {Object}
 */
function shortCutsItem(env) {
    return {
        type: "item",
        id: "shortcuts",
        hide: env.isSmall,
        description: markup`
            <div class="d-flex align-items-center justify-content-between p-0 w-100">
                <span>${_t("Shortcuts")}</span>
                <span class="fw-bold">${isMacOS() ? "CMD" : "CTRL"}+K</span>
            </div>`,
        callback: () => {
            env.services.command.openMainPalette({
                FooterComponent: ShortcutsFooterComponent,
            });
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

/**
 * User menu item factory: "My Preferences" (opens res.users form).
 * @param {Object} env
 * @returns {Object}
 */
export function preferencesItem(env) {
    return {
        type: "item",
        id: "preferences",
        description: _t("My Preferences"),
        callback: async function () {
            const actionDescription = await env.services.orm.call(
                "res.users",
                "action_get",
            );
            actionDescription.res_id = user.userId;
            env.services.action.doAction(actionDescription);
        },
        sequence: 50,
    };
}

/**
 * User menu item factory: "My Odoo.com Account" (opens external link).
 * @param {Object} env
 * @returns {Object}
 */
export function odooAccountItem(env) {
    return {
        type: "item",
        id: "account",
        description: _t("My Odoo.com Account"),
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

/**
 * User menu item factory: "Install App" (PWA install prompt or scoped app).
 * @param {Object} env
 * @returns {Object}
 */
function installPWAItem(env) {
    let description = _t("Install App");
    let callback = () => env.services.pwa.show();
    let show = () => env.services.pwa.isAvailable;
    const currentApp = env.services.menu.getCurrentApp();
    if (
        currentApp &&
        ["barcode", "field-service", "shop-floor"].includes(currentApp.actionPath)
    ) {
        // While the feature could work with all apps, we have decided to only
        // support the installation of the apps contained in this list
        // The list can grow in the future, by simply adding their path
        description = _t("Install %s", currentApp.name);
        callback = () => {
            window.open(
                `/scoped_app?app_id=${currentApp.webIcon.split(",")[0]}&path=${encodeURIComponent(
                    `scoped_app/${currentApp.actionPath}`,
                )}`,
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

/**
 * User menu item factory: "Log out".
 * @param {Object} env
 * @returns {Object}
 */
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
            browser.navigator.serviceWorker?.controller?.postMessage("user_logout");
            browser.location.href = route;
        },
        sequence: 70,
    };
}

registry
    .category("user_menuitems")
    .add("support", supportItem)
    .add("shortcuts", shortCutsItem)
    .add("separator", separator)
    .add("preferences", preferencesItem)
    .add("odoo_account", odooAccountItem)
    .add("install_pwa", installPWAItem)
    .add("log_out", logOutItem);
