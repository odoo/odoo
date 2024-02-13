/** @odoo-module */

import { App } from "@odoo/owl";
import { defineRootNode, getActiveElement } from "@web/../lib/hoot-dom/helpers/dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { HootError } from "../hoot_utils";

/**
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

const FIXTURE_OFFSET = -10_000; // In pixels
const FIXTURE_COMMON_STYLE = ["display: block", "height: 100vh", "position: fixed", "width: 100vw"];
const FIXTURE_DEBUG_STYLE = [
    ...FIXTURE_COMMON_STYLE,
    "background-color: inherit",
    "color: inherit",
    "left: 0",
    "top: 0",
    "z-index: 3",
].join(";");
const FIXTURE_STYLE = [
    ...FIXTURE_COMMON_STYLE,
    `left: ${FIXTURE_OFFSET}px`,
    "opacity: 0",
    `top: ${FIXTURE_OFFSET}px`,
].join(";");

customElements.define("hoot-fixture", class HootFixture extends HTMLElement {});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {import("./runner").TestRunner} runner
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
            if (runner.debug) {
                fixture.setAttribute("style", FIXTURE_DEBUG_STYLE);
            } else {
                fixture.setAttribute("style", FIXTURE_STYLE);
            }

            setupEventActions(fixture);

            document.body.appendChild(fixture);
        }
        return fixture;
    };

    /**
     * @param {Parameters<typeof import("@odoo/owl").mount>[0]} ComponentClass
     * @param {Parameters<typeof import("@odoo/owl").mount>[2]} config
     * @param {Parameters<typeof import("@odoo/owl").mount>[1]} [target]
     */
    const mountOnFixture = (ComponentClass, config, target) => {
        if (target && !fixture) {
            throw new HootError(`Cannot mount on a custom target before the fixture is created.`);
        }

        const app = new App(ComponentClass, {
            name: `TEST: ${ComponentClass.name}`,
            test: true,
            warnIfNoStaticProps: true,
            ...config,
        });

        runner.after(() => app.destroy());

        return app.mount(target || getFixture());
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
