/** @odoo-module **/

import { isMacOS } from "@web/core/browser/feature_detection";
import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";
import { session } from "@web/session";

const { Component } = owl;

function documentationItem(env) {
    const documentationURL = "https://www.odoo.com/documentation/master";
    return {
        type: "item",
        id: "documentation",
        description: env._t("Documentation"),
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
        description: env._t("Support"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

class ShortcutsFooterComponent extends Component {
    setup() {
        this.runShortcutKey = isMacOS() ? "ALT + CONTROL" : "ALT";
    }
}
ShortcutsFooterComponent.template = "web.UserMenu.ShortcutsFooterComponent";

function shortCutsItem(env) {
    return {
        type: "item",
        id: "shortcuts",
        hide: env.isSmall,
        description: env._t("Shortcuts"),
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
        description: env._t("Preferences"),
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
        description: env._t("My Odoo.com account"),
        callback: () => {
            env.services
                .rpc("/web/session/account")
                .then((url) => {
                    browser.location.href = url;
                })
                .catch(() => {
                    browser.location.href = "https://accounts.odoo.com/account";
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
        description: env._t("Log out"),
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
