/** @odoo-module */

import { after } from "@odoo/hoot";
import { getFixture } from "@odoo/hoot-dom";
import { App, Component, xml } from "@odoo/owl";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { URL } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {import("@odoo/owl").ComponentConstructor | string} component
 * @param {any} appConfig
 */
export async function mount(component, appConfig) {
    if (typeof component === "string") {
        component = class extends Component {
            static template = xml`${component}`;
        };
    }

    const app = new App(component, { ...appConfig, test: true });
    const comp = await app.mount(getFixture());

    after(() => app.destroy());

    return comp;
}

/**
 * @param {string} url
 */
export function parseUrl(url) {
    return new URL(url).pathname.replace(/(\.test)?\.js$/, "");
}
