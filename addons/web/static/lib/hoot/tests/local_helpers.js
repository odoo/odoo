/** @odoo-module */

import { after, getFixture } from "@odoo/hoot";
import { App, Component, xml } from "@odoo/owl";
import { Runner } from "../core/runner";
import { undefineTags } from "../core/tag";
import { RunnerPlugin } from "../ui/runner_plugin";
import { UiPlugin } from "../ui/ui_plugin";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function makeTestRunner() {
    const runner = new Runner();
    after(() => undefineTags(runner.tags.keys()));
    return runner;
}

/**
 * @param {import("@odoo/owl").ComponentConstructor} ComponentClass
 * @param {Parameters<import("@odoo/owl").mount>[2]} [params]
 */
export async function mountForTest(ComponentClass, params) {
    if (typeof ComponentClass === "string") {
        ComponentClass = class extends Component {
            static name = "anonymous component";
            static template = xml`${ComponentClass}`;
        };
    }

    const app = new App({
        name: "TEST",
        plugins: [RunnerPlugin, UiPlugin],
        test: true,
        config: params?.config,
    });
    const fixture = getFixture();

    after(() => app.destroy());

    fixture.style.backgroundColor = "#fff";
    await app.createRoot(ComponentClass, { props: params?.props }).mount(fixture);
    if (fixture.hasIframes) {
        await fixture.waitForIframes();
    }
}

/**
 * @param {string} url
 */
export function parseUrl(url) {
    return url.replace(/^.*hoot\/tests/, "@hoot").replace(/(\.test)?\.js$/, "");
}
