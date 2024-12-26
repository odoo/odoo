/** @odoo-module */

import { after, destroy, getFixture } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { App, Component, xml } from "@odoo/owl";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export async function mountForTest(ComponentClass) {
    if (typeof ComponentClass === "string") {
        ComponentClass = class extends Component {
            static name = "anonymous component";
            static props = {};
            static template = xml`${ComponentClass}`;
        };
    }

    const app = new App(ComponentClass, {
        name: "TEST",
        test: true,
        warnIfNoStaticProps: true,
    });
    after(() => destroy(app));
    return app.mount(getFixture());
}

/**
 * @param {string} url
 */
export function parseUrl(url) {
    return url.replace(/^.*hoot\/tests/, "@hoot").replace(/(\.test)?\.js$/, "");
}

export function waitForIframes() {
    return Promise.all(
        queryAll("iframe").map(
            (iframe) => new Promise((resolve) => iframe.addEventListener("load", resolve))
        )
    );
}
