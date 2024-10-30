/** @odoo-module */

import { App, Component, xml } from "@odoo/owl";
import {
    defineRootNode,
    getActiveElement,
    getCurrentDimensions,
} from "@web/../lib/hoot-dom/helpers/dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { HootError } from "../hoot_utils";
import { queryOne } from "@odoo/hoot-dom";

/**
 * @typedef {Parameters<typeof import("@odoo/owl").mount>} MountParameters
 *
 * @typedef {{
 *  component: import("@odoo/owl").ComponentConstructor;
 *  props: unknown;
 * }} TestRootProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { customElements, document, getSelection, HTMLElement } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const FIXTURE_COMMON_STYLE = [
    "position: fixed",
    "height: 100vh",
    "width: 100vw",
    "left: 50%",
    "top: 50%",
    "transform: translate(-50%, -50%)",
];
const FIXTURE_DEBUG_STYLE = [
    ...FIXTURE_COMMON_STYLE,
    "background-color: inherit",
    "color: inherit",
    "z-index: 3",
].join(";");
const FIXTURE_STYLE = [...FIXTURE_COMMON_STYLE, "opacity: 0", "z-index: -1"].join(";");

const destroyed = new WeakSet();

customElements.define("hoot-fixture", class HootFixture extends HTMLElement {});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {App | Component} target
 */
export function destroy(target) {
    const app = target instanceof App ? target : target.__owl__.app;
    if (destroyed.has(app)) {
        return;
    }
    destroyed.add(app);
    app.destroy();
}

/**
 * @param {import("./runner").Runner} runner
 */
export function makeFixtureManager(runner) {
    const cleanupFixture = () => {
        allowFixture = false;
        if (!fixture) {
            return;
        }
        shouldPrepareNextFixture = true;
        fixture.remove();
        fixture = null;
    };

    const getFixture = () => {
        if (!allowFixture) {
            throw new HootError(`Cannot access fixture outside of a test.`);
        }
        if (!fixture) {
            fixture = document.createElement("hoot-fixture");
            if (runner.debug || runner.config.headless) {
                fixture.setAttribute("style", FIXTURE_DEBUG_STYLE);
            } else {
                fixture.setAttribute("style", FIXTURE_STYLE);
            }

            const { width, height } = getCurrentDimensions();
            fixture.style.width = `${width}px`;
            fixture.style.height = `${height}px`;

            setupEventActions(fixture);

            document.body.appendChild(fixture);
        }
        return fixture;
    };

    /**
     * @param {MountParameters[0] | string} ComponentClass
     * @param {MountParameters[2]} config
     * @param {import("@odoo/hoot-dom").Target} [target]
     */
    const mountOnFixture = (ComponentClass, config, target) => {
        if (target && !fixture) {
            throw new HootError(`Cannot mount on a custom target before the fixture is created.`);
        }

        if (typeof ComponentClass === "string") {
            ComponentClass = class extends Component {
                static props = {};
                static template = xml`${ComponentClass}`;
            };
        }

        const app = new App(ComponentClass, {
            name: `TEST: ${ComponentClass.name}`,
            test: true,
            warnIfNoStaticProps: true,
            ...config,
        });

        runner.after(() => destroy(app));

        return app.mount(target ? queryOne(target) : getFixture());
    };

    const setupFixture = () => {
        allowFixture = true;
        if (!shouldPrepareNextFixture) {
            return;
        }
        shouldPrepareNextFixture = false;

        // Reset focus & selection
        getActiveElement().blur();
        getSelection().removeAllRanges();
    };

    let allowFixture = false;
    /** @type {HTMLElement | null} */
    let fixture = null;
    let shouldPrepareNextFixture = true; // Prepare setup for first test

    runner.beforeAll(() => {
        defineRootNode(getFixture);
    });
    runner.afterAll(() => {
        defineRootNode(null);
    });

    return {
        cleanup: cleanupFixture,
        setup: setupFixture,
        get: getFixture,
        mount: mountOnFixture,
    };
}
