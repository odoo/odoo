/** @odoo-module */

import { after, getFixture } from "@odoo/hoot";
import { App } from "@odoo/owl";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { URL } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @template {import("@odoo/owl").ComponentConstructor | string} T
 * @param {T} component
 * @param {any} appConfig
 * @returns {T extends string ? void : Promise<import("@odoo/owl").Component>}
 */
export function mount(component, appConfig) {
    if (typeof component === "string") {
        const fixture = getFixture();
        fixture.innerHTML = component;

        after(() => {
            fixture.innerHTML = "";
        });
        return;
    }

    const app = new App(component, { ...appConfig, test: true });

    after(() => app.destroy());

    return app.mount(getFixture());
}

/**
 * @param {string} url
 */
export function parseUrl(url) {
    return url.replace(/^.*hoot\/tests/, "@hoot").replace(/(\.test)?\.js$/, "");
}
