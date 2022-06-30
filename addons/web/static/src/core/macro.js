/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

// rough approximation of a visible element. not perfect (does not take into
// account opacity = 0 for example), but good enough for our purpose
function isVisible(e) {
    return e.offsetWidth > 0 || e.offsetHeight > 0;
}

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

class TimeoutError extends Error {}

class Macro {
    constructor(descr) {
        this.name = descr.name || "anonymous";
        this.timeoutDuration = descr.timeout || 0;
        this.timeout = null;
        this.currentIndex = 0;
        this.interval = "interval" in descr ? Math.max(16, descr.interval) : 500;
        this.isComplete = false;
        this.steps = descr.steps;
        this.onStep = descr.onStep || (() => {});
        this.onError = descr.onError;
        this.onTimeout = descr.onTimeout;
        this.setTimer();
    }

    advance() {
        if (this.isComplete) {
            return;
        }
        const step = this.steps[this.currentIndex];
        let trigger = step.trigger;
        if (trigger) {
            let el = null;
            if (typeof trigger === "function") {
                const result = this.safeCall(trigger);
                if (result instanceof HTMLElement) {
                    el = result;
                }
            }
            if (typeof trigger === "string") {
                el = document.querySelector(trigger);
            }
            if (el && isVisible(el)) {
                this.advanceStep(el, step);
            }
        } else {
            // a step without a trigger is just an action
            this.advanceStep(null, step);
        }
    }

    advanceStep(el, step) {
        this.safeCall(this.onStep, el, step);
        const action = step.action;
        if (action in ACTION_HELPERS) {
            ACTION_HELPERS[action](el, step);
        } else if (typeof action === "function") {
            this.safeCall(action, el);
        }
        this.currentIndex++;
        if (this.currentIndex === this.steps.length) {
            this.isComplete = true;
            browser.clearTimeout(this.timeout);
        } else {
            this.setTimer();
            this.advance();
        }
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
    constructor(target = document.body) {
        this.isRunning = false;
        this.timeout = null;
        this.target = target;
        this.interval = Infinity; // nbr of ms before we check the dom to advance macros
        this.macros = new Set();
        this.observer = new MutationObserver(this.delayedCheck.bind(this));
    }

    async activate(descr) {
        // micro task tick to make sure we add the macro in a new call stack,
        // so we are guaranteed that we are not iterating on the current macros
        await Promise.resolve();
        const macro = new Macro(descr);
        this.interval = Math.min(this.interval, macro.interval);
        this.macros.add(macro);
        this.start();
    }

    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            this.observer.observe(this.target, {
                attributes: true,
                childList: true,
                subtree: true,
                characterData: true,
            });
        }
        this.delayedCheck();
    }

    stop() {
        if (this.isRunning) {
            this.isRunning = false;
            browser.clearTimeout(this.timeout);
            this.timeout = null;
            this.observer.disconnect();
        }
    }

    delayedCheck() {
        if (this.timeout) {
            browser.clearTimeout(this.timeout);
        }
        this.timeout = browser.setTimeout(this.advanceMacros.bind(this), this.interval);
    }

    advanceMacros() {
        let toDelete = [];
        for (let macro of this.macros) {
            macro.advance();
            if (macro.isComplete) {
                toDelete.push(macro);
            }
        }
        if (toDelete.length) {
            for (let macro of toDelete) {
                this.macros.delete(macro);
            }
            // recompute current interval, because it may need to be increased
            this.interval = Infinity;
            for (let macro of this.macros) {
                this.interval = Math.min(this.interval, macro.interval);
            }
        }
        if (this.macros.size === 0) {
            this.stop();
        }
    }
}
