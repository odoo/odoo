/** @odoo-module **/

import { whenReady } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";

import { switchColorSchemeItem } from "./color_scheme_menu_items";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

export class ColorSchemeService {
    constructor(env, { ui }) {
        this.ui = ui;
        whenReady(() => this.applyColorScheme());
    }
    /**
     * @returns {String} The color scheme configured by the end-user
     */
    get activeColorScheme() {
        return cookie.get("configured_color_scheme") || cookie.get("color_scheme") || "light";
    }
    /**
     * @returns {String} the color scheme that should be loaded from the server
     */
    get effectiveColorScheme() {
        return this.activeColorScheme;
    }
    /**
     * @param {String} scheme
     */
    switchToColorScheme(scheme) {
        cookie.set("configured_color_scheme", scheme);
        this.applyColorScheme();
    }
    /**
     * Check if the currently loaded assets correspond to the current effective
     * color scheme. If not, reload the page to get the correct assets.
     */
    applyColorScheme() {
        const effectiveScheme = this.effectiveColorScheme;
        if (effectiveScheme !== (cookie.get("color_scheme") || "light")) {
            cookie.set("color_scheme", effectiveScheme);
            this.ui.block();
            this.reload();
        }
    }
    /**
     * Force the page's reload
     */
    reload() {
        browser.location.reload();
    }
}

export const colorSchemeService = {
    dependencies: ["ui"],

    start(env, services) {
        userMenuRegistry.add("color_scheme.switch", switchColorSchemeItem);
        return new ColorSchemeService(env, services);
    },
};
serviceRegistry.add("color_scheme", colorSchemeService);
