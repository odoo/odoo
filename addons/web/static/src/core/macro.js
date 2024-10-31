import { browser } from "@web/core/browser/browser";
import { isVisible } from "@web/core/utils/ui";
import { validate } from "@odoo/owl";
import { Mutex } from "./utils/concurrency";

const macroSchema = {
    name: { type: String, optional: true },
    timeout: { type: Number, optional: true },
    debounceDelay: { type: Number, optional: true }, //Delay before checking if element is in DOM.
    stepDelay: { type: Number, optional: true }, //Wait this delay between steps
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
    debouncedFindTrigger = null;
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
        this.timerDuration = this.timeout || 0;
        this.debounceDelay = Math.max(this.debounceDelay || 100, 50);
        this.onComplete = this.onComplete || (() => {});
        this.onStep = this.onStep || (() => {});

        this.stepElFound = new Array(this.steps.length).fill(false);
        this.stepHasStarted = new Array(this.steps.length).fill(false);
        this.observer = new MacroMutationObserver(() => this.continue("mutation"));
    }

    async continue(from) {
        //Only one case, when browser refresh just after the last step.
        if (!this.currentStep && this.currentIndex === 0) {
            await delay(300);
            this.stop();
        }
        // Make sure to take the only possible path.
        // A step always starts with "next".
        // A step can only be continued with "mutation".
        // We abort when the macro is finished or if a mutex occurs afterwards.
        if (
            this.isComplete ||
            (from === "next" && this.stepHasStarted[this.currentIndex]) ||
            (from === "mutation" && !this.stepHasStarted[this.currentIndex]) ||
            (from === "mutation" && this.currentElement)
        ) {
            return;
        }
        let delay = this.debounceDelay;
        // Called only once per step.
        if (!this.stepHasStarted[this.currentIndex]) {
            this.setTimer();
            this.stepHasStarted[this.currentIndex] = true;
            if (!this.currentStep.trigger) {
                await this.doAction();
            }
            delay = 150;
            if (this.currentStep?.initialDelay) {
                const initialDelay = parseFloat(this.currentStep.initialDelay());
                delay = initialDelay >= 0 ? initialDelay : delay;
            }
        }
        if (this.currentStep?.trigger && !this.currentElement) {
            this.debounceFindTrigger(delay);
        }
    }

    async findTrigger() {
        if (this.isComplete) {
            return;
        }
        const trigger = this.currentStep.trigger;
        if (!trigger) {
            this.stop(`A trigger is needed to find trigger !`);
        }
        try {
            if (typeof trigger === "function") {
                this.currentElement = this.safeCall(trigger);
            } else if (typeof trigger === "string") {
                const triggerEl = document.querySelector(trigger);
                this.currentElement = isVisible(triggerEl) && triggerEl;
            }
        } catch (error) {
            this.stop(`Error when trying to find trigger: ${error.message}`);
        }
        // RUN ACTION
        if (this.currentElement) {
            await this.doAction();
        }
    }

    async doAction() {
        this.clearTimer();
        let actionResult = false;
        try {
            const action = this.currentStep.action;
            if (action in ACTION_HELPERS) {
                actionResult = ACTION_HELPERS[action](this.currentElement, this.currentStep);
            } else if (typeof action === "function") {
                actionResult = await this.safeCall(action, this.currentElement);
            }
        } catch (error) {
            this.stop(`Step failed when try to run action : ${error.message}`);
        }
        this.increment();
        await this.waitStepDelay();
        if (!actionResult) {
            await this.continue("next");
        }
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
        const timeout = this.currentStep.timeout || 10000;
        this.timer = browser.setTimeout(() => {
            if (this.currentStep.onTimeout) {
                this.safeCall(this.currentStep.onTimeout, this.currentStep, this.currentIndex);
            } else {
                this.stop("Step timeout");
            }
        }, timeout);
    }

    clearTimer() {
        this.resetDebounce();
        if (this.timer) {
            browser.clearTimeout(this.timer);
        }
    }

    resetDebounce() {
        if (this.debouncedFindTrigger) {
            browser.clearTimeout(this.debouncedFindTrigger);
        }
    }

    debounceFindTrigger(delay) {
        this.resetDebounce();
        this.debouncedFindTrigger = browser.setTimeout(
            () => mutex.exec(() => this.findTrigger()),
            delay
        );
    }

    start(target) {
        this.observer.observe(target);
        this.continue("next");
    }

    stop(error) {
        this.clearTimer();
        this.observer.disconnect();
        this.isComplete = true;
        if (error) {
            if (this.onError) {
                this.onError(error, this.currentStep, this.currentIndex);
            } else {
                console.error(error);
            }
        } else if (this.currentIndex === this.steps.length) {
            mutex.getUnlockedDef().then(() => {
                this.onComplete();
            });
        }
        return;
    }

    async waitStepDelay() {
        // await new Promise((resolve) => requestAnimationFrame(resolve));
        if (this.stepDelay) {
            await new Promise((resolve) => browser.setTimeout(resolve, this.stepDelay));
        }
        return;
    }
}

export class MacroEngine {
    constructor(params = {}) {
        this.isRunning = false;
        this.target = params.target || document.body;
        this.macros = new Set();
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
        }
        this.advanceMacros();
    }

    async stop() {
        if (this.isRunning) {
            this.isRunning = false;
        }
        for (const macro of this.macros) {
            macro.stop();
        }
        this.clean();
    }

    clean() {
        for (const macro of this.macros) {
            if (macro.isComplete) {
                this.macros.delete(macro);
            }
        }
    }

    async advanceMacros() {
        await Promise.all([...this.macros].map((macro) => macro.start(this.target)));
        this.clean();
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
