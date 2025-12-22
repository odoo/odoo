/** @odoo-module */

import { App } from "@odoo/owl";
import { getActiveElement, getCurrentDimensions } from "@web/../lib/hoot-dom/helpers/dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { isInstanceOf } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { HootError } from "../hoot_utils";
import { subscribeToTransitionChange } from "../mock/animation";
import { getViewPortHeight, getViewPortWidth } from "../mock/window";

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

const { customElements, document, getSelection, HTMLElement, Promise, WeakSet } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {HTMLIFrameElement} iframe
 */
function waitForIframe(iframe) {
    return new Promise((resolve) => iframe.addEventListener("load", resolve));
}

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
    const app = isInstanceOf(target, App) ? target : target.__owl__.app;
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
    function cleanup() {
        allowFixture = false;

        if (currentFixture) {
            shouldPrepareNextFixture = true;
            currentFixture.remove();
            currentFixture = null;
        }
    }

    function getFixture() {
        if (!allowFixture) {
            throw new HootError(`cannot access fixture outside of a test.`);
        }
        if (!currentFixture) {
            // Prepare fixture once to not force layouts/reflows
            currentFixture = document.createElement(HootFixtureElement.TAG_NAME);
            if (runner.debug || runner.headless) {
                currentFixture.show();
            }

            const { width, height } = getCurrentDimensions();
            if (width !== getViewPortWidth()) {
                currentFixture.style.width = `${width}px`;
            }
            if (height !== getViewPortHeight()) {
                currentFixture.style.height = `${height}px`;
            }

            document.body.appendChild(currentFixture);
        }
        return currentFixture;
    }

    function setup() {
        allowFixture = true;

        if (shouldPrepareNextFixture) {
            shouldPrepareNextFixture = false;

            // Reset focus & selection
            getActiveElement().blur();
            getSelection().removeAllRanges();
        }
    }

    return {
        cleanup,
        setup,
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

        this.styleElement.id = "hoot-fixture-style";
        this.styleElement.textContent = /* css */ `
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

    get hasIframes() {
        return this._iframes.size > 0;
    }

    /** @private */
    _observer = new MutationObserver(this._onFixtureMutation.bind(this));
    /**
     * @private
     * @type {Map<HTMLIFrameElement, Promise<void>>}
     */
    _iframes = new Map();

    connectedCallback() {
        setupEventActions(this);
        subscribeToTransitionChange((allowTransitions) =>
            this.classList.toggle(this.constructor.CLASSES.transitions, allowTransitions)
        );

        this._observer.observe(this, { childList: true, subtree: true });
        this._lookForIframes();
    }

    disconnectedCallback() {
        this._iframes.clear();
        this._observer.disconnect();
    }

    hide() {
        this.classList.remove(this.constructor.CLASSES.show);
    }

    async waitForIframes() {
        await Promise.all(this._iframes.values());
    }

    show() {
        this.classList.add(this.constructor.CLASSES.show);
    }

    /**
     * @private
     */
    _lookForIframes() {
        const toRemove = new Set(this._iframes.keys());
        for (const iframe of this.getElementsByTagName("iframe")) {
            if (toRemove.delete(iframe)) {
                continue;
            }
            this._iframes.set(iframe, waitForIframe(iframe));
            setupEventActions(iframe.contentWindow);
        }
        for (const iframe of toRemove) {
            this._iframes.delete(iframe);
        }
    }

    /**
     * @private
     * @type {MutationCallback}
     */
    _onFixtureMutation(mutations) {
        if (mutations.some((mutation) => mutation.addedNodes)) {
            this._lookForIframes();
        }
    }
}
