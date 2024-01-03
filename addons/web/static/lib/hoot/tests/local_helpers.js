/** @odoo-module */

import { after, getFixture } from "@odoo/hoot";
import { App, Component, xml } from "@odoo/owl";

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
 */
export async function mount(component, appConfig) {
    if (typeof component === "string") {
        component = class extends Component {
            static props = {};
            static template = xml`${component}`;
        };
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
