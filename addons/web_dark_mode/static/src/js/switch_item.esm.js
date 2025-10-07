/** @odoo-module **/

import {browser} from "@web/core/browser/browser";
import {registry} from "@web/core/registry";

export function darkModeSwitchItem(env) {
    return {
        type: "switch",
        id: "color_scheme.switch",
        description: env._t("Dark Mode"),
        callback: () => {
            env.services.color_scheme.switchColorScheme();
        },
        isChecked: env.services.cookie.current.color_scheme === "dark",
        sequence: 40,
    };
}

export const colorSchemeService = {
    dependencies: ["cookie", "orm", "ui", "user"],

    async start(env, {cookie, orm, ui, user}) {
        registry.category("user_menuitems").add("darkmode", darkModeSwitchItem);

        if (!cookie.current.color_scheme) {
            const match_media = window.matchMedia("(prefers-color-scheme: dark)");
            const dark_mode = match_media.matches;
            cookie.setCookie("color_scheme", dark_mode ? "dark" : "light");
            if (dark_mode) browser.location.reload();
        }

        return {
            async switchColorScheme() {
                const scheme =
                    cookie.current.color_scheme === "dark" ? "light" : "dark";
                cookie.setCookie("color_scheme", scheme);

                await orm.write("res.users", [user.userId], {
                    dark_mode: scheme === "dark",
                });

                ui.block();
                browser.location.reload();
            },
        };
    },
};

registry.category("services").add("color_scheme", colorSchemeService);
