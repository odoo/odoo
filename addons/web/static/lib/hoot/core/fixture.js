/** @odoo-module */

import { App } from "@odoo/owl";
import {
    defineRootNode,
    getActiveElement,
    getCurrentDimensions,
} from "@web/../lib/hoot-dom/helpers/dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { HootError } from "../hoot_utils";

/**
 * @typedef {Parameters<typeof import("@odoo/owl").mount>[2] & {
 *  className: string | string[];
 *  target?: import("@odoo/hoot-dom").Target;
 * }} MountOnFixtureOptions
 *
 * @typedef {{
 *  component: import("@odoo/owl").ComponentConstructor;
 *  props: unknown;
 * }} TestRootProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { customElements, document, getSelection, HTMLElement, WeakSet } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

class HootFixtureElement extends HTMLElement {
    connectedCallback() {
        currentFixture = this;
    }

    disconnectedCallback() {
        currentFixture = null;
    }
}

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
let allowFixture = false;
/** @type {HootFixtureElement | null} */
let currentFixture = null;
let shouldPrepareNextFixture = true; // Prepare setup for first test

customElements.define("hoot-fixture", HootFixtureElement);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {App | import("@odoo/owl").Component} target
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
        if (!currentFixture) {
            return;
        }
        shouldPrepareNextFixture = true;
        currentFixture.remove();
    };

    const getFixture = () => {
        if (!allowFixture) {
            throw new HootError(`Cannot access fixture outside of a test.`);
        }
        if (!currentFixture) {
            // Prepare fixture once to not force layouts/reflows
            const preFixture = document.createElement("hoot-fixture");
            if (runner.debug || runner.config.headless) {
                preFixture.setAttribute("style", FIXTURE_DEBUG_STYLE);
            } else {
                preFixture.setAttribute("style", FIXTURE_STYLE);
            }

            const { width, height } = getCurrentDimensions();
            preFixture.style.width = `${width}px`;
            preFixture.style.height = `${height}px`;

            setupEventActions(preFixture);

            document.body.appendChild(preFixture);
        }
        return currentFixture;
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
    };
}
