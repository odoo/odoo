import { browser } from "@web/core/browser/browser";
import { isVisible } from "@web/core/utils/ui";
import { delay, Mutex } from "@web/core/utils/concurrency";
import { validate } from "@odoo/owl";

const macroSchema = {
    name: { type: String, optional: true },
    checkDelay: { type: Number, optional: true }, //Delay before checking if element is in DOM.
    stepDelay: { type: Number, optional: true }, //Wait this delay between steps
    timeout: { type: Number, optional: true },
    steps: {
        type: Array,
        element: {
            initialDelay: { type: Function, optional: true },
            action: { type: Function },
            trigger: { type: [Function, String], optional: true },
            timeout: { type: Number, optional: true },
            onTimeout: { type: Function, optional: true },
        },
    },
    onComplete: { type: Function, optional: true },
    onStep: { type: Function, optional: true },
    onError: { type: Function, optional: true },
    onTimeout: { type: Function, optional: true },
};

/**
 * @typedef MacroStep
 * @property {string} [trigger]
 * - An action returning a "truthy" value means that the step isn't successful.
 * - Current step index won't be incremented.
 * @property {string | (el: Element, step: MacroStep) => undefined | string} [action]
 * @property {*} [*] - any payload to the step.
 *
 * @typedef MacroDescriptor
 * @property {() => Element | undefined} trigger
 * @property {() => {}} action
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

class Macro {
    currentIndex = 0;
    isComplete = false;
    errored = false;
    constructor(descr) {
        try {
            validate(descr, macroSchema);
        } catch (error) {
            throw new Error(
                `Error in schema for Macro ${JSON.stringify(descr, null, 4)}\n${error.message}`
            );
        }
        Object.assign(this, descr);
        this.name = this.name || "anonymous";
        this.onComplete = this.onComplete || (() => {});
        this.onStep = this.onStep || (() => {});
        this.stepElFound = new Array(this.steps.length).fill(false);
    }

    async advance() {
        //Only one case, when browser refresh just after the last step.
        if (!this.currentStep && this.currentIndex === 0) {
            await delay(300);
            this.stop();
        }
        if (this.isComplete) {
            return;
        }
        this.setTimer();
        let proceedToAction = true;
        if (this.currentStep.trigger) {
            proceedToAction = this.findTrigger();
        }
        if (proceedToAction) {
            this.safeCall(this.onStep, this.currentElement, this.currentStep);
            const actionResult = await this.performAction();
            this.clearTimer();
            if (!actionResult) {
                // If falsy action result, it means the action worked properly.
                // So we can proceed to the next step.
                this.increment();
                await this.advance();
            }
        }
    }

    /**
     * Find the trigger and assess whether it can continue on performing the actions.
     * @returns {boolean}
     */
    findTrigger() {
        if (this.isComplete) {
            return;
        }
        const trigger = this.currentStep.trigger;
        try {
            if (typeof trigger === "function") {
                this.currentElement = this.safeCall(trigger);
            } else if (typeof trigger === "string") {
                const triggerEl = document.querySelector(trigger);
                this.currentElement = isVisible(triggerEl) && triggerEl;
            } else {
                throw new Error(`Trigger can only be string or function.`);
            }
        } catch (error) {
            this.stop(`Error when trying to find trigger: ${error.message}`);
        }
        return !!this.currentElement;
    }

    /**
     * Calls the `step.action` expecting no return to be successful.
     */
    async performAction() {
        let actionResult;
        try {
            const action = this.currentStep.action;
            if (action in ACTION_HELPERS) {
                actionResult = ACTION_HELPERS[action](this.currentElement, this.currentStep);
            } else if (typeof action === "function") {
                actionResult = await this.safeCall(action, this.currentElement);
            }
        } catch (error) {
            this.stop(`ERROR IN ACTION: ${error.message}`);
        }
        return actionResult;
    }

    get currentStep() {
        return this.steps[this.currentIndex];
    }

    get currentElement() {
        return this.stepElFound[this.currentIndex];
    }

    set currentElement(value) {
        this.stepElFound[this.currentIndex] = value;
    }

    increment() {
        this.currentIndex++;
        if (this.currentIndex >= this.steps.length) {
            this.stop();
        }
    }

    safeCall(fn, ...args) {
        if (this.isComplete) {
            return;
        }
        try {
            return fn(...args);
        } catch (e) {
            this.stop(e);
        }
    }

    /**
     * Timer for findTrigger only (not for doing action)
     */
    setTimer() {
        this.clearTimer();
        const timeout = this.currentStep.timeout || this.timeout;
        if (timeout > 0) {
            this.timer = browser.setTimeout(() => {
                if (this.currentStep.onTimeout) {
                    this.safeCall(this.currentStep.onTimeout, this.currentStep, this.currentIndex);
                } else {
                    this.stop("Step timeout");
                }
            }, timeout);
        }
    }

    clearTimer() {
        if (this.timer) {
            browser.clearTimeout(this.timer);
        }
    }

    stop(error) {
        this.clearTimer();
        this.isComplete = true;
        if (error) {
            this.errored = true;
            if (this.onError) {
                this.onError(error, this.currentStep, this.currentIndex);
            } else {
                console.error(error);
            }
        } else if (this.currentIndex === this.steps.length && !this.errored) {
            mutex.getUnlockedDef().then(() => {
                this.onComplete();
            });
        }
        return;
    }
}

export class MacroEngine {
    constructor(params = {}) {
        this.isRunning = false;
        this.timeout = null;
        this.target = params.target || document.body;
        this.defaultCheckDelay = params.defaultCheckDelay ?? 750;
        this.macros = new Set();
        this.macroMutationObserver = new MacroMutationObserver(() => this.delayedCheck());
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
            this.macroMutationObserver.observe(this.target);
        }
        this.delayedCheck();
    }

    stop() {
        if (this.isRunning) {
            this.isRunning = false;
            browser.clearTimeout(this.timeout);
            this.timeout = null;
            this.macroMutationObserver.disconnect();
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

export class MacroMutationObserver {
    observerOptions = {
        attributes: true,
        childList: true,
        subtree: true,
        characterData: true,
    };
    constructor(callback) {
        this.callback = callback;
        this.observer = new MutationObserver((mutationList, observer) => {
            callback();
            mutationList.forEach((mutationRecord) =>
                Array.from(mutationRecord.addedNodes).forEach((node) => {
                    let iframes = [];
                    if (String(node.tagName).toLowerCase() === "iframe") {
                        iframes = [node];
                    } else if (node instanceof HTMLElement) {
                        iframes = Array.from(node.querySelectorAll("iframe"));
                    }
                    iframes.forEach((iframeEl) =>
                        this.observeIframe(iframeEl, observer, () => callback())
                    );
                    this.findAllShadowRoots(node).forEach((shadowRoot) =>
                        observer.observe(shadowRoot, this.observerOptions)
                    );
                })
            );
        });
    }
    disconnect() {
        this.observer.disconnect();
    }
    findAllShadowRoots(node, shadowRoots = []) {
        if (node.shadowRoot) {
            shadowRoots.push(node.shadowRoot);
            this.findAllShadowRoots(node.shadowRoot, shadowRoots);
        }
        node.childNodes.forEach((child) => {
            this.findAllShadowRoots(child, shadowRoots);
        });
        return shadowRoots;
    }
    observe(target) {
        this.observer.observe(target, this.observerOptions);
        //When iframes already exist at "this.target" initialization
        target
            .querySelectorAll("iframe")
            .forEach((el) => this.observeIframe(el, this.observer, () => this.callback()));
        //When shadowDom already exist at "this.target" initialization
        this.findAllShadowRoots(target).forEach((shadowRoot) => {
            this.observer.observe(shadowRoot, this.observerOptions);
        });
    }
    observeIframe(iframeEl, observer, callback) {
        const observerOptions = {
            attributes: true,
            childList: true,
            subtree: true,
            characterData: true,
        };
        const observeIframeContent = () => {
            if (iframeEl.contentDocument) {
                iframeEl.contentDocument.addEventListener("load", (event) => {
                    callback();
                    observer.observe(event.target, observerOptions);
                });
                if (!iframeEl.src || iframeEl.contentDocument.readyState === "complete") {
                    callback();
                    observer.observe(iframeEl.contentDocument, observerOptions);
                }
            }
        };
        observeIframeContent();
        iframeEl.addEventListener("load", observeIframeContent);
    }
}
