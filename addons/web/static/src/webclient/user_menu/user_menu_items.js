import { Component, markup, plugin } from "@odoo/owl";
import { isDisplayStandalone, isMacOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { router } from "@web/core/browser/router";
import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";
import { post } from "@web/core/network/http_service";
import { redirect } from "@web/core/utils/urls";
import { useService } from "@web/core/utils/hooks";
import { ORM } from "@web/core/orm_plugin";

function supportItem() {
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

function shortCutsItem() {
    const command = useService("command");
    const ui = useService("ui");

    return {
        type: "item",
        id: "shortcuts",
        hide: ui.isSmall,
        description: markup`
            <div class="d-flex align-items-center justify-content-between p-0 w-100">
                <span>${_t("Shortcuts")}</span>
                <span class="fw-bold">${isMacOS() ? "CMD" : "CTRL"}+K</span>
            </div>`,
        callback: () => {
            command.openMainPalette({ FooterComponent: ShortcutsFooterComponent });
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

export function preferencesItem() {
    const action = useService("action");
    const orm = plugin(ORM);

    return {
        type: "item",
        id: "preferences",
        description: _t("My Preferences"),
        callback: async function () {
            const actionDescription = await orm.call("res.users", "action_get");
            actionDescription.res_id = user.userId;
            action.doAction(actionDescription);
        },
        sequence: 50,
    };
}

export function odooAccountItem() {
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

function installPWAItem() {
    const pwa = useService("pwa");
    const menu = useService("menu");

    let description = _t("Install App");
    let callback = () => pwa.show();
    let hide = !pwa.isAvailable || isDisplayStandalone();
    const currentApp = menu.getCurrentApp();
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
        hide = pwa.isScopedApp;
    }
    return {
        type: "item",
        id: "install_pwa",
        description,
        callback,
        hide,
        sequence: 65,
    };
}

function logOutItem() {
    const pwa = useService("pwa");
    let route = "/web/session/logout";
    if (pwa.isScopedApp) {
        route += `?redirect=${encodeURIComponent(pwa.startUrl)}`;
    }
    return {
        type: "item",
        id: "logout",
        description: _t("Log out"),
        callback: async () => {
            browser.navigator.serviceWorker?.controller?.postMessage("user_logout");
            const url = await post(route, { csrf_token: odoo.csrf_token }, "url");
            redirect(url);
        },
        sequence: 70,
    };
}

export function shareUrlMenuItem() {
    const ui = useService("ui");
    return {
        type: "item",
        hide: !router.shareUrl || ui.isSmall || !isDisplayStandalone(),
        id: "share_url",
        description: markup`
            <div class="d-flex align-items-center justify-content-between w-100">
                <span>${_t("Share")}</span>
                <span class="fa fa-share-alt"></span>
            </div>`,
        callback: router.shareUrl,
        sequence: 25,
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
    .add("log_out", logOutItem)
    .add("share_url", shareUrlMenuItem);
