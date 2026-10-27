/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { isVisible } from "@web/core/utils/ui";
import { Mutex } from "@web/core/utils/concurrency";

/**
 * @typedef MacroStep
 * @property {string} [trigger]
 * - An action returning a "truthy" value means that the step isn't successful.
 * - Current step index won't be incremented.
 * @property {string | (el: Element, step: MacroStep) => undefined | string} [action]
 * @property {*} [*] - any payload to the step.
 */

export const ACTION_HELPERS = {
    click(el, _step) {
        el.dispatchEvent(new MouseEvent("mouseover"));
        el.dispatchEvent(new MouseEvent("mouseenter"));
        el.dispatchEvent(new MouseEvent("mousedown"));
        el.dispatchEvent(new MouseEvent("mouseup"));
        el.click();
        el.dispatchEvent(new MouseEvent("mouseout"));
        el.dispatchEvent(new MouseEvent("mouseleave"));
    },
    text(el, step) {
        // simulate an input (probably need to add keydown/keyup events)
        this.click(el, step);
        el.value = step.value;
        el.dispatchEvent(new InputEvent("input", { bubbles: true }));
        el.dispatchEvent(new InputEvent("change", { bubbles: true }));
    },
};

const mutex = new Mutex();

class TimeoutError extends Error {}

class Macro {
    constructor(descr) {
        this.name = descr.name || "anonymous";
        this.timeoutDuration = descr.timeout || 0;
        this.timeout = null;
        this.currentIndex = 0;
        this.checkDelay = descr.checkDelay || 0;
        this.isComplete = false;
        this.steps = descr.steps;
        this.onStep = descr.onStep || (() => {});
        this.onError = descr.onError;
        this.onTimeout = descr.onTimeout;
        this.setTimer();
    }

    async advance() {
        if (this.isComplete) {
            return;
        }
        const step = this.steps[this.currentIndex];
        const [proceedToAction, el] = this.checkTrigger(step);
        if (proceedToAction) {
            this.safeCall(this.onStep, el, step);
            const actionResult = await this.performAction(el, step);
            if (!actionResult) {
                // If falsy action result, it means the action worked properly.
                // So we can proceed to the next step.
                this.currentIndex++;
                if (this.currentIndex === this.steps.length) {
                    this.isComplete = true;
                    browser.clearTimeout(this.timeout);
                } else {
                    this.setTimer();
                    await this.advance();
                }
            }
        }
    }

    /**
     * Find the trigger and assess whether it can continue on performing the actions.
     * @param {{ trigger: string | () => Element | null }} param0
     * @returns {[proceedToAction: boolean; el: Element | undefined]}
     */
    checkTrigger({ trigger }) {
        let el;

        if (!trigger) {
            return [true, el];
        }

        if (typeof trigger === "function") {
            el = this.safeCall(trigger);
        } else if (typeof trigger === "string") {
            const triggerEl = document.querySelector(trigger);
            el = isVisible(triggerEl) && triggerEl;
        } else {
            throw new Error(`Trigger can only be string or function.`);
        }

        if (el) {
            return [true, el];
        } else {
            return [false, el];
        }
    }

    /**
     * Calls the `step.action` expecting no return to be successful.
     * @param {Element} el
     * @param {Step} step
     */
    async performAction(el, step) {
        const action = step.action;
        let actionResult;
        if (action in ACTION_HELPERS) {
            actionResult = ACTION_HELPERS[action](el, step);
        } else if (typeof action === "function") {
            actionResult = await this.safeCall(action, el, step);
        }
        return actionResult;
    }

    safeCall(fn, ...args) {
        if (this.isComplete) {
            return;
        }
        try {
            return fn(...args);
        } catch (e) {
            this.handleError(e);
        }
    }

    setTimer() {
        if (this.timeoutDuration) {
            browser.clearTimeout(this.timeout);
            this.timeout = browser.setTimeout(() => {
                if (this.onTimeout) {
                    const index = this.currentIndex;
                    const step = this.steps[index];
                    this.safeCall(this.onTimeout, step, index);
                } else {
                    const error = new TimeoutError("Step timeout");
                    this.handleError(error);
                }
            }, this.timeoutDuration);
        }
    }

    handleError(error) {
        // mark the macro as complete, so it can be cleaned up from the
        // engine
        this.isComplete = true;
        browser.clearTimeout(this.timeout);
        if (this.onError) {
            const index = this.currentIndex;
            const step = this.steps[index];
            this.onError(error, step, index);
        } else {
            console.error(error);
        }
    }
}

export class MacroEngine {
    constructor(params = {}) {
        this.isRunning = false;
        this.timeout = null;
        this.target = params.target || document.body;
        this.defaultCheckDelay = params.defaultCheckDelay ?? 750;
        this.macros = new Set();
        this.observerOptions = {
            attributes: true,
            childList: true,
            subtree: true,
            characterData: true,
        };
        this.observer = new MutationObserver(this.delayedCheck.bind(this));
        this.iframeObserver = new MutationObserver(() => {
            const iframeEl = document.querySelector("iframe.o_iframe");
            if (iframeEl) {
                iframeEl.addEventListener("load", () => {
                    if (iframeEl.contentDocument) {
                        this.observer.observe(iframeEl.contentDocument, this.observerOptions);
                    }
                });
                // If the iframe was added without a src, its load event was immediately fired and
                // will not fire again unless another src is set. Unfortunately, the case of this
                // happening and the iframe content being altered programmaticaly may happen.
                // (E.g. at the moment this was written, the mass mailing editor iframe is added
                // without src and its content rewritten immediately afterwards).
                if (!iframeEl.src) {
                    if (iframeEl.contentDocument) {
                        this.observer.observe(iframeEl.contentDocument, this.observerOptions);
                    }
                }
            }
        });
    }

    async activate(descr, exclusive = false) {
        if (this.exclusive) {
            return;
        }
        this.exclusive = exclusive;
        // micro task tick to make sure we add the macro in a new call stack,
        // so we are guaranteed that we are not iterating on the current macros
        await Promise.resolve();
        const macro = new Macro(descr);
        if (exclusive) {
            this.macros = new Set([macro]);
        } else {
            this.macros.add(macro);
        }
        this.start();
    }

    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            this.observer.observe(this.target, this.observerOptions);
            this.iframeObserver.observe(this.target, { childList: true, subtree: true });
        }
        this.delayedCheck();
    }

    stop() {
        if (this.isRunning) {
            this.isRunning = false;
            browser.clearTimeout(this.timeout);
            this.timeout = null;
            this.observer.disconnect();
            this.iframeObserver.disconnect();
        }
    }

    delayedCheck() {
        if (this.timeout) {
            browser.clearTimeout(this.timeout);
        }
        this.timeout = browser.setTimeout(
            () => mutex.exec(this.advanceMacros.bind(this)),
            this.getCheckDelay() || this.defaultCheckDelay
        );
    }

    getCheckDelay() {
        // If a macro has a checkDelay different from 0, use it. Select the minimum.
        // For example knowledge has a macro with a delay of 10ms. We don't want to wait
        // longer because of other running tours.
        return [...this.macros]
            .map((m) => m.checkDelay)
            .filter((delay) => delay > 0)
            .reduce((m, v) => Math.min(m, v), this.defaultCheckDelay);
    }

    async advanceMacros() {
        await Promise.all([...this.macros].map((macro) => macro.advance()));
        for (const macro of this.macros) {
            if (macro.isComplete) {
                this.macros.delete(macro);
            }
        }
        if (this.macros.size === 0) {
            this.stop();
        }
    }
}
