/** @odoo-module */

import { App, Component } from "@odoo/owl";
import { defineRootNode, getActiveElement } from "@web/../lib/hoot-dom/helpers/dom";
import { resetEventActions } from "@web/../lib/hoot-dom/helpers/events";

/**
 * @typedef {{
 *  component: typeof Component;
 *  props: unknown;
 * }} TestRootProps
 */

//-----------------------------------------------------------------------------
// Globals
//-----------------------------------------------------------------------------

const { customElements, document, getSelection, HTMLElement } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const FIXTURE_DEBUG_STYLE = "display: block; width: 100vw; height: 100vh;";
const FIXTURE_STYLE =
    FIXTURE_DEBUG_STYLE + " opacity: 0; position: fixed; left: -10000px; top: -10000px;";

customElements.define("hoot-fixture", class HootFixture extends HTMLElement {});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {import("./runner").TestRunner} runner
 */
export function makeFixtureManager(runner) {
    const cleanupFixture = () => {
        if (!fixture) {
            return;
        }
        shouldPrepareNextFixture = true;
        fixture.remove();
        fixture = null;
    };

    const getFixture = () => {
        if (!fixture) {
            resetEventActions();

            fixture = document.createElement("hoot-fixture");
            if (runner.debug) {
                fixture.setAttribute("style", FIXTURE_DEBUG_STYLE);
            } else {
                fixture.setAttribute("style", FIXTURE_STYLE);
            }

            document.body.appendChild(fixture);
        }
        return fixture;
    };

    /**
     * @param {Parameters<typeof import("@odoo/owl").mount>[0]} ComponentClass
     * @param {Parameters<typeof import("@odoo/owl").mount>[2]} config
     */
    const mountOnFixture = (ComponentClass, config) => {
        const app = new App(ComponentClass, {
            name: `TEST: ${ComponentClass.name}`,
            test: true,
            warnIfNoStaticProps: true,
            ...config,
        });

        runner.after(() => app.destroy());

        return app.mount(getFixture());
    };

    const setupFixture = () => {
        if (!shouldPrepareNextFixture) {
            return;
        }
        shouldPrepareNextFixture = false;

        // Reset focus & selection
        getActiveElement().blur();
        getSelection().removeAllRanges();
    };

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
