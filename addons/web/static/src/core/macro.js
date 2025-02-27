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

class MacroStep {
    constructor(step, index) {
        Object.assign(this, step);
        this.index = index;
    }

    get debounceDelay() {
        let delay = this.index === 0 ? 0 : 50;
        if (this.initialDelay) {
            const initialDelay = parseFloat(this.initialDelay());
            delay = initialDelay >= 0 ? initialDelay : delay;
        }
        return delay;
    }

    async performAction(trigger) {
        if (!this.action) {
            return;
        }
        try {
            return await this.action(trigger);
        } catch (error) {
            throw new MacroError("Action", `ERROR during perform action:\n${error.message}`, {
                cause: error,
            });
        }
    }

    async waitFor() {
        if (!this.trigger) {
            return;
        }
        try {
            return await this.waitUntil(() => {
                if (typeof this.trigger === "function") {
                    return this.trigger();
                } else if (typeof this.trigger === "string") {
                    const triggerEl = document.querySelector(this.trigger);
                    return isVisible(triggerEl) && triggerEl;
                }
            });
        } catch (error) {
            throw new MacroError("Trigger", `ERROR during find trigger:\n${error.message}`, {
                cause: error,
            });
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

    get currentStep() {
        return new MacroStep(this.steps[this.currentIndex], this.currentIndex);
    }

    async start() {
        await waitForStable();
        await this.advance();
    }

    async advance() {
        if (this.isComplete || this.currentIndex >= this.steps.length) {
            await this.stop();
        }
        try {
            await Promise.race([this.step(), this.stepTimeout()]);
        } catch (error) {
            await this.stop(error);
        }
        this.currentIndex++;
        await this.advance();
    }

    async step() {
        if (this.currentStep.debounceDelay > 0) {
            await delay(this.currentStep.debounceDelay);
        }
        const trigger = await this.currentStep.waitFor();
        await this.onStep({ ...this.currentStep }, trigger, this.currentIndex);
        const actionResult = await this.currentStep.performAction(trigger);
        if (actionResult) {
            await this.stop();
        }
    }

    async stepTimeout() {
        const timeout = this.currentStep.timeout || this.timeout || 10000;
        await delay(timeout);
        throw new MacroError("Timeout", `TIMEOUT step failed to complete within ${timeout} ms.`);
    }

    async stop(error) {
        if (this.isComplete) {
            return;
        }
        await waitForStable();
        this.isComplete = true;
        if (error) {
            this.onError(error, { ...this.currentStep }, this.currentIndex);
        } else if (this.currentIndex === this.steps.length) {
            this.onComplete();
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
