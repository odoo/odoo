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
            type: Object,
            shape: {
                action: { type: [Function, String], optional: true },
                timeout: { type: Number, optional: true },
                trigger: { type: [Function, String], optional: true },
                value: { type: [String, Number], optional: true },
            },
            validate: (step) => {
                return step.action || step.trigger;
            },
        },
    },
    onComplete: { type: Function, optional: true },
    onStep: { type: Function, optional: true },
    onError: { type: Function, optional: true },
};

const mutex = new Mutex();

class MacroError extends Error {
    constructor(type, message, options) {
        super(message, options);
        this.type = type;
    }
}

export async function waitForStable(target = document, timeout = 1000 / 16) {
    return new Promise((resolve) => {
        let observer;
        let timer;
        const mutationList = [];
        function onMutation(mutations) {
            mutationList.push(...(mutations || []));
            clearTimeout(timer);
            timer = setTimeout(() => {
                observer.disconnect();
                resolve(mutationList);
            }, timeout);
        }
        observer = new MacroMutationObserver(onMutation);
        observer.observe(target);
        onMutation([]);
    });
}

export class Macro {
    currentIndex = 0;
    isComplete = false;
    calledBack = false;
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
        this.onError =
            this.onError ||
            ((e) => {
                console.error(e);
            });
        this.stepElFound = new Array(this.steps.length).fill(false);
        this.stepHasStarted = new Array(this.steps.length).fill(false);
        this.observer = new MacroMutationObserver(() => this.debounceAdvance("mutation"));
    }

    async start(target = document) {
        this.observer.observe(target);
        this.debounceAdvance("next");
    }

    getDebounceDelay() {
        let delay = Math.max(this.checkDelay ?? 750, 50);
        // Called only once per step.
        if (!this.stepHasStarted[this.currentIndex]) {
            delay = this.currentIndex === 0 ? 0 : 50;
            this.stepHasStarted[this.currentIndex] = true;
        }
        return delay;
    }

    async advance() {
        if (this.isComplete) {
            return;
        }
        if (this.currentStep.trigger) {
            this.setTimer();
        }
        let proceedToAction = true;
        if (this.currentStep.trigger) {
            proceedToAction = this.findTrigger();
        }
        if (proceedToAction) {
            this.onStep(this.currentElement, this.currentStep, this.currentIndex);
            this.clearTimer();
            const actionResult = await this.stepAction(this.currentElement);
            if (!actionResult) {
                // If falsy action result, it means the action worked properly.
                // So we can proceed to the next step.
                this.currentIndex++;
                if (this.currentIndex >= this.steps.length) {
                    this.stop();
                }
                this.debounceAdvance("next");
            }
        }
    }

    /**
     * Find the trigger and assess whether it can continue on performing the actions.
     * @returns {boolean}
     */
    findTrigger() {
        const { trigger } = this.currentStep;
        if (this.isComplete) {
            return;
        }
        try {
            if (typeof trigger === "function") {
                this.currentElement = trigger();
            } else if (typeof trigger === "string") {
                const triggerEl = document.querySelector(trigger);
                this.currentElement = isVisible(triggerEl) && triggerEl;
            } else {
                throw new Error(`Trigger can only be string or function.`);
            }
        } catch (error) {
            this.stop(
                new MacroError("Trigger", `ERROR during find trigger:\n${error.message}`, {
                    cause: error,
                })
            );
        }
        return !!this.currentElement;
    }

    /**
     * Must not return anything for macro to continue.
     */
    async stepAction(element) {
        const { action } = this.currentStep;
        if (this.isComplete || !action) {
            return;
        }
        try {
            return await action(element);
        } catch (error) {
            this.stop(
                new MacroError("Action", `ERROR during perform action:\n${error.message}`, {
                    cause: error,
                })
            );
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

    /**
     * Timer for findTrigger only (not for doing action)
     */
    setTimer() {
        this.clearTimer();
        const timeout = this.currentStep.timeout || this.timeout;
        if (timeout > 0) {
            this.timer = browser.setTimeout(() => {
                this.stop(
                    new MacroError(
                        "Timeout",
                        `TIMEOUT step failed to complete within ${timeout} ms.`
                    )
                );
            }, timeout);
        }
    }

    clearTimer() {
        this.resetDebounce();
        if (this.timer) {
            browser.clearTimeout(this.timer);
        }
    }

    resetDebounce() {
        if (this.debouncedAdvance) {
            browser.clearTimeout(this.debouncedAdvance);
        }
    }

    /**
     * @param {"next"|"mutation"} from
     */
    async debounceAdvance(from) {
        this.resetDebounce();
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
        // When browser refresh just after the last step.
        if (!this.currentStep && this.currentIndex === 0) {
            await delay(300);
            this.stop();
        } else if (from === "next" && !this.currentStep.trigger) {
            this.advance();
        } else {
            this.debouncedAdvance = browser.setTimeout(
                () => mutex.exec(() => this.advance()),
                this.getDebounceDelay()
            );
        }
    }

    stop(error) {
        this.clearTimer();
        this.isComplete = true;
        this.observer.disconnect();
        if (!this.calledBack) {
            this.calledBack = true;
            if (error) {
                this.onError(error, this.currentStep, this.currentIndex);
            } else if (this.currentIndex === this.steps.length) {
                mutex.getUnlockedDef().then(() => {
                    this.onComplete();
                });
            }
        }
        return;
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
            callback(mutationList);
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
