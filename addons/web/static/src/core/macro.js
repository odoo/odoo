import { delay } from "@web/core/utils/concurrency";
import { isVisible } from "@web/core/utils/ui";
import { validate } from "@odoo/owl";

const macroSchema = {
    checkDelay: { type: Number, optional: true }, //Delay before checking if element is in DOM.
    steps: {
        type: Array,
        element: {
            tyep: Object,
            shape: {
                action: { type: Function, optional: true },
                trigger: { type: [Function, String], optional: true },
                timeout: { type: Number, optional: true },
                initialDelay: { type: Function, optional: true },
            },
        },
    },
    name: { type: String, optional: true },
    timeout: { type: Number, optional: true },
    onComplete: { type: Function, optional: true },
    onError: { type: Function, optional: true },
    onStep: { type: Function, optional: true },
};

export class MacroTimeoutError extends Error {}
export class MacroTriggerError extends Error {}
export class MacroActionError extends Error {}

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
        this.onComplete = this.onComplete || (() => {});
        this.onStep = this.onStep || (() => {});
    }

    get currentStep() {
        return this.steps[this.currentIndex];
    }

    get debounceDelay() {
        let delay = this.currentIndex === 0 ? 0 : 50;
        if (this.currentStep?.initialDelay) {
            const initialDelay = parseFloat(this.currentStep.initialDelay());
            delay = initialDelay >= 0 ? initialDelay : delay;
        }
        return delay;
    }

    async start() {
        // When macro start
        await waitForStable();
        // When last step is a redirection
        if (!this.currentStep) {
            //To avoid getComputedStyle errors, let a delay
            await delay(3000);
            this.stop();
        }
        await this.continue();
    }

    async continue() {
        if (this.isComplete || this.currentIndex >= this.steps.length) {
            this.stop();
            return;
        }
        if (this.debounceDelay > 0) {
            await delay(this.debounceDelay);
        }
        const trigger = await this.findTrigger();
        await this.onStep(this.currentStep, trigger, this.currentIndex);
        await this.performAction(trigger);
        this.currentIndex++;
        await this.continue();
    }

    async findTrigger() {
        const { trigger, timeout } = this.currentStep;
        if (this.isComplete || !trigger) {
            return;
        }
        try {
            return await this.waitUntil(() => {
                if (typeof trigger === "function") {
                    return trigger();
                } else if (typeof trigger === "string") {
                    const triggerEl = document.querySelector(trigger);
                    return isVisible(triggerEl) && triggerEl;
                }
            }, timeout || this.timeout || 10000);
        } catch (error) {
            this.stop(error);
        }
    }

    /**
     * Calls the `step.action` expecting no return to be successful.
     */
    async performAction(trigger) {
        const { action } = this.currentStep;
        if (this.isComplete || !action) {
            return;
        }
        try {
            const actionResult = await action(trigger);
            if (actionResult) {
                this.stop();
            }
        } catch (error) {
            this.stop(new MacroActionError(error));
        }
    }

    stop(error) {
        if (this.isComplete) {
            return;
        }
        this.isComplete = true;
        if (error) {
            if (typeof this.onError === "function") {
                this.onError(error, this.currentStep, this.currentIndex);
            } else {
                console.error(error.message);
            }
        } else if (this.currentIndex === this.steps.length) {
            this.onComplete();
        }
    }

    async waitUntil(predicate, timeout = 10000) {
        const tryToPredicate = () => {
            try {
                return predicate();
            } catch (error) {
                throw new MacroTriggerError(error);
            }
        };
        const result = tryToPredicate();
        if (result) {
            return Promise.resolve(result);
        }
        let handle;
        let timeoutId;
        let running = true;
        return new Promise((resolve, reject) => {
            const runCheck = () => {
                const result = tryToPredicate();
                if (result) {
                    resolve(result);
                } else if (running) {
                    handle = requestAnimationFrame(runCheck);
                } else {
                    reject(new MacroTimeoutError(timeout));
                }
            };
            handle = requestAnimationFrame(runCheck);
            timeoutId = setTimeout(() => (running = false), timeout);
        }).finally(() => {
            cancelAnimationFrame(handle);
            clearTimeout(timeoutId);
        });
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
