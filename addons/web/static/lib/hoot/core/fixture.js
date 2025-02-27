/** @odoo-module */

import { App } from "@odoo/owl";
import {
    defineRootNode,
    getActiveElement,
    getCurrentDimensions,
} from "@web/../lib/hoot-dom/helpers/dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { HootError } from "../hoot_utils";
import { subscribeToTransitionChange } from "../mock/animation";

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

const destroyed = new WeakSet();
let allowFixture = false;
/** @type {HootFixtureElement | null} */
let currentFixture = null;
let shouldPrepareNextFixture = true; // Prepare setup for first test

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

        if (currentFixture) {
            shouldPrepareNextFixture = true;
            currentFixture.remove();
        }
    };

    const getFixture = () => {
        if (!allowFixture) {
            throw new HootError(`Cannot access fixture outside of a test.`);
        }
        if (!currentFixture) {
            // Prepare fixture once to not force layouts/reflows
            /** @type {HootFixtureElement} */
            const fixture = document.createElement(HootFixtureElement.TAG_NAME);
            if (runner.debug || runner.config.headless) {
                fixture.show();
            }

            const { width, height } = getCurrentDimensions();
            if (width !== window.innerWidth) {
                fixture.style.width = `${width}px`;
            }
            if (height !== window.innerHeight) {
                fixture.style.height = `${height}px`;
            }

            document.body.appendChild(fixture);
        }
        return currentFixture;
    };

    const setupFixture = () => {
        allowFixture = true;

        if (shouldPrepareNextFixture) {
            shouldPrepareNextFixture = false;

            // Reset focus & selection
            getActiveElement().blur();
            getSelection().removeAllRanges();
        }

        return cleanupFixture;
    };

    runner.beforeAll(() => {
        defineRootNode(getFixture);
    });
    runner.afterAll(() => {
        defineRootNode(null);
    });

    return {
        setup: setupFixture,
        get: getFixture,
    };
}

export class HootFixtureElement extends HTMLElement {
    static CLASSES = {
        transitions: "allow-transitions",
        show: "show-fixture",
    };
    static TAG_NAME = "hoot-fixture";

    static styleElement = document.createElement("style");

    static {
        customElements.define(this.TAG_NAME, this);
        this.styleElement.innerText = /* css */ `
            ${this.TAG_NAME} {
                position: fixed !important;
                height: 100vh;
                width: 100vw;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%);
                opacity: 0;
                z-index: -1;
            }

            ${this.TAG_NAME}.${this.CLASSES.show} {
                background-color: inherit;
                color: inherit;
                opacity: 1;
                z-index: 3;
            }

            ${this.TAG_NAME}:not(.${this.CLASSES.transitions}) * {
                animation: none !important;
                transition: none !important;
            }
        `;
    }

    /** @type {(() => any) | null} */
    cleanupEventActions = null;

    connectedCallback() {
        currentFixture = this;

        this.cleanupEventActions = setupEventActions(this);
        subscribeToTransitionChange((allowTransitions) =>
            this.classList.toggle(this.constructor.CLASSES.transitions, allowTransitions)
        );
    }

    disconnectedCallback() {
        currentFixture = null;

        this.cleanupEventActions?.();
    }

    hide() {
        this.classList.remove(this.constructor.CLASSES.show);
    }

    show() {
        this.classList.add(this.constructor.CLASSES.show);
    }
}
