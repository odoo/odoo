import { isVisible } from "@web/core/utils/ui";
import { delay } from "@web/core/utils/concurrency";
import { validate } from "@odoo/owl";

const macroSchema = {
    name: { type: String, optional: true },
    timeout: { type: Number, optional: true },
    steps: {
        type: Array,
        element: {
            type: Object,
            shape: {
                action: { type: [Function, String], optional: true },
                initialDelay: { type: Function, optional: true },
                timeout: { type: Number, optional: true },
                trigger: { type: [Function, String], optional: true },
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
        this.onError =
            this.onError ||
            ((error, step, index) => {
                console.error(error.message, step, index);
            });
    }

    async start() {
        // When macro start
        await waitForStable();
        // When last step is a redirection
        if (!this.currentStep) {
            //To avoid get_actionComputedStyle errors, let a delay
            await delay(3000);
            this.stop();
        }
        await this.advance();
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

    async advance() {
        if (this.isComplete) {
            this.stop();
            return;
        }
        if (this.currentIndex >= this.steps.length) {
            await waitForStable();
            this.stop();
            return;
        }
        try {
            await Promise.race([this.step(), this.stepTimeout()]);
        } catch (error) {
            this.stop(error);
        }
        this.currentIndex++;
        await this.advance();
    }

    async stepAction(trigger) {
        const { action } = this.currentStep;
        if (this.isComplete || !action) {
            return;
        }
        try {
            return await action(trigger);
        } catch (error) {
            throw new MacroError("Action", `ERROR during perform action:\n${error.message}`, {
                cause: error,
            });
        }
    }

    async stepTimeout() {
        const timeout = this.currentStep.timeout || this.timeout || 10000;
        await delay(timeout);
        throw new MacroError("Timeout", `TIMEOUT step failed to complete within ${timeout} ms.`);
    }

    async stepTrigger() {
        const { trigger } = this.currentStep;
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
            });
        } catch (error) {
            throw new MacroError("Trigger", `ERROR during find trigger:\n${error.message}`, {
                cause: error,
            });
        }
    }

    async step() {
        if (this.debounceDelay > 0) {
            await delay(this.debounceDelay);
        }
        const trigger = await this.stepTrigger();
        await this.onStep(this.currentStep, trigger, this.currentIndex);
        const actionResult = await this.stepAction(trigger);
        if (actionResult) {
            this.stop();
        }
    }

    stop(error) {
        if (this.isComplete) {
            return;
        }
        this.isComplete = true;
        if (error) {
            this.onError(error, this.currentStep, this.currentIndex);
        } else if (this.currentIndex === this.steps.length) {
            this.onComplete();
        }
    }

    async waitUntil(predicate) {
        const result = predicate();
        if (result) {
            return Promise.resolve(result);
        }
        let handle;
        return new Promise((resolve) => {
            const runCheck = () => {
                const result = predicate();
                if (result) {
                    resolve(result);
                }
                handle = requestAnimationFrame(runCheck);
            };
            handle = requestAnimationFrame(runCheck);
        }).finally(() => {
            cancelAnimationFrame(handle);
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
