/** @odoo-module */

import { animationFrame } from "@odoo/hoot-dom";
import { getActiveElement, getCurrentDimensions } from "@web/../lib/hoot-dom/helpers/dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
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

const { customElements, document, getSelection, HTMLElement, MutationObserver, Promise } =
    globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {HTMLIFrameElement} iframe
 */
function waitForIframe(iframe) {
    return new Promise((resolve) => iframe.addEventListener("load", resolve));
}

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class FixtureManager {
    allowFixture = false;
    /** @type {HootFixtureElement | null} */
    currentFixture = null;
    shouldPrepareNextFixture = true; // Prepare setup for first test

    /**
     * @param {Runner} runner
     */
    constructor(runner) {
        this.runner = runner;

        // Pre-bind all methods
        this.cleanup = this.cleanup.bind(this);
        this.getFixture = this.getFixture.bind(this);
        this.setup = this.setup.bind(this);
    }

    cleanup() {
        this.allowFixture = false;

        if (this.currentFixture) {
            this.shouldPrepareNextFixture = true;
            this.currentFixture.remove();
            this.currentFixture = null;
        }
    }

    getFixture() {
        if (!this.allowFixture) {
            throw new HootError(`cannot access fixture outside of a test.`);
        }
        if (!this.currentFixture) {
            // Prepare fixture once to not force layouts/reflows
            this.currentFixture = document.createElement(HootFixtureElement.TAG_NAME);
            if (this.runner.debug || this.runner.headless) {
                this.currentFixture.show();
            }

            const { width, height } = getCurrentDimensions();
            if (width !== getViewPortWidth()) {
                this.currentFixture.style.width = `${width}px`;
            }
            if (height !== getViewPortHeight()) {
                this.currentFixture.style.height = `${height}px`;
            }

            document.body.appendChild(this.currentFixture);
        }
        return this.currentFixture;
    }

    async setup() {
        this.allowFixture = true;

        if (this.shouldPrepareNextFixture) {
            this.shouldPrepareNextFixture = false;

            // Reset focus & selection
            getActiveElement().blur();
            getSelection().removeAllRanges();
            // Wait for selectionchange events to expire before any actual testing.
            await animationFrame();
        }
    }
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
