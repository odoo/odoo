/** @odoo-module **/

import { Component, markup } from "@odoo/owl";
import { isMacOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import { session } from "@web/session";
import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";

function documentationItem(env) {
    const documentationURL = "https://www.odoo.com/documentation/master";
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
    setup() {
        this.runShortcutKey = isMacOS() ? "CONTROL" : "ALT";
    }
}
ShortcutsFooterComponent.template = "web.UserMenu.ShortcutsFooterComponent";

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
            actionDescription.res_id = env.services.user.userId;
            env.services.action.doAction(actionDescription);
        },
        sequence: 50,
    };
}

function odooAccountItem(env) {
    return {
        type: "item",
        id: "account",
        description: _t("My Odoo.com account"),
        callback: () => {
            env.services
                .rpc("/web/session/account")
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

function logOutItem(env) {
    const route = "/web/session/logout";
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
    .add("log_out", logOutItem);
