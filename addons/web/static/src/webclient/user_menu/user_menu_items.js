/** @odoo-module **/

import { Dialog } from "../../core/dialog/dialog";
import { browser } from "../../core/browser/browser";
import { registry } from "../../core/registry";
import { _lt } from "../../core/l10n/translation";
import { session } from "@web/session";

function documentationItem(env) {
    const documentationURL = "https://www.odoo.com/documentation/15.0";
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

class ShortCutsDialog extends Dialog {}
ShortCutsDialog.bodyTemplate = "web.UserMenu.shortcutsTable";
ShortCutsDialog.title = _lt("Shortcuts");

function shortCutsItem(env) {
    return {
        type: "item",
        id: "shortcuts",
        hide: env.isSmall,
        description: env._t("Shortcuts"),
        callback: () => {
            env.services.dialog.add(ShortCutsDialog);
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
        description: env._t("My Odoo.com.account"),
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
