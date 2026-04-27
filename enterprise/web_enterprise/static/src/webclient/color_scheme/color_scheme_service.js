import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";

import { switchColorSchemeItem } from "./color_scheme_menu_items";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

export const colorSchemeService = {
    dependencies: ["ui"],

    start(env, { ui }) {
        userMenuRegistry.add("color_scheme.switch", switchColorSchemeItem);
        return {
            switchToColorScheme: (scheme) => {
                cookie.set("color_scheme", scheme);
                ui.block();
                this.reload();
            },
        };
    },
    reload() {
        browser.location.reload();
    },
};
serviceRegistry.add("color_scheme", colorSchemeService);
