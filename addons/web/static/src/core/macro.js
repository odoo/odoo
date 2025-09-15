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
                timeout: { type: Number, optional: true },
                trigger: { type: [Function, String], optional: true },
            },
            validate: (step) => step.action || step.trigger,
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

async function performAction(trigger, action) {
    if (!action) {
        return;
    }
    try {
        return await action(trigger);
    } catch (error) {
        throw new MacroError(
            "Action",
            error.stack || `ERROR during perform action: ${error.message}`,
            {cause: error}
        );
    }
}

async function waitForTrigger(trigger) {
    if (!trigger) {
        return;
    }
    try {
        await delay(50);
        return await waitUntil(() => {
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

export async function waitUntil(predicate) {
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
        await this.advance();
    }

    async advance() {
        if (this.isComplete || this.currentIndex >= this.steps.length) {
            this.stop();
            return;
        }
        try {
            const step = this.steps[this.currentIndex];
            const timeoutDelay = step.timeout || this.timeout || 10000;
            const executeStep = async () => {
                const trigger = await waitForTrigger(step.trigger);
                const result = await performAction(trigger, step.action);
                await this.onStep({ step, trigger, index: this.currentIndex });
                return result;
            };
            const launchTimer = async () => {
                await delay(timeoutDelay);
                throw new MacroError(
                    "Timeout",
                    `TIMEOUT step failed to complete within ${timeoutDelay} ms.`
                );
            };
            // If falsy action result, it means the action worked properly.
            // So we can proceed to the next step.
            const actionResult = await Promise.race([executeStep(), launchTimer()]);
            if (actionResult) {
                this.stop();
                return;
            }
        } catch (error) {
            this.stop(error);
            return;
        }
        this.currentIndex++;
        await this.advance();
    }

    stop(error) {
        if (this.isComplete) {
            return;
        }
        this.isComplete = true;
        if (error) {
            const step = this.steps[this.currentIndex];
            this.onError({ error, step, index: this.currentIndex });
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
