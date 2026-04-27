/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import mobile from "@web_mobile/js/services/core";

export function shortcutItem(env) {
    return {
        type: "item",
        id: "web_mobile.shortcut",
        description: _t("Add to Home Screen"),
        callback: () => {
            const menu = env.services.menu.getCurrentApp();
            if (menu) {
                const base64Icon = menu.webIconData;
                mobile.methods.addHomeShortcut({
                    title: document.title,
                    shortcut_url: document.URL,
                    web_icon: base64Icon.substring(base64Icon.indexOf(",") + 1),
                });
            } else {
                env.services.notification.add(_t("No shortcut for Home Menu"));
            }
        },
        sequence: 100,
    };
}

export function switchAccountItem(env) {
    return {
        type: "item",
        id: "web_mobile.switch",
        description: _t("Switch/Add Account"),
        callback: () => {
            mobile.methods.switchAccount();
        },
        sequence: 100,
    };
}
