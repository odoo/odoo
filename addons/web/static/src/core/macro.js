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
                willUnload: {
                    type: [Boolean, String],
                    optional: true,
                    validate(value) {
                        return [true, false, "continue"].includes(value);
                    },
                },
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
        throw new MacroError("Action", `ERROR during perform action:\n${error.message}`, {
            cause: error,
        });
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

async function waitUntil(predicate) {
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
        this.listenBeforeUnloadEvents();
        await this.advance();
    }

    async advance() {
        if (this.isComplete || this.currentIndex >= this.steps.length) {
            this.stop();
            return;
        }
        try {
            const currentStep = this.steps[this.currentIndex];
            const executeStep = async () => {
                if (currentStep.willUnload) {
                    sessionStorage.setItem("waitForUnload", "1");
                    //Will stop at the end of currentStep
                    if (currentStep.willUnload !== "continue") {
                        this.isComplete = true;
                    }
                }
                const trigger = await waitForTrigger(currentStep.trigger);
                await this.onStep(currentStep, trigger, this.currentIndex);
                return await performAction(trigger, currentStep.action);
            };
            const launchTimer = async () => {
                const timeout_delay = currentStep.timeout || this.timeout || 10000;
                await delay(timeout_delay);
                throw new MacroError(
                    "Timeout",
                    `TIMEOUT step failed to complete within ${timeout_delay} ms.`
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
            this.onError(error, this.steps[this.currentIndex], this.currentIndex);
        } else if (this.currentIndex === this.steps.length) {
            this.onComplete();
        }
    }

    listenBeforeUnloadEvents() {
        sessionStorage.removeItem("waitForUnload");
        const handleUnloadEvent = () => {
            const waitForUnload = sessionStorage.getItem("waitForUnload");
            if (!waitForUnload) {
                const message = `
                    Be sure to use { willUnload: true } for any step
                    that involves firing a beforeUnload or pageHide event.
                    This avoid a non-deterministic behavior by explicitly stopping 
                    the macro that might continue before the page is unloaded.
                `.replace(/^\s+/gm, "");
                const error = new MacroError("AuthorizeBeforeUnload", message);
                this.stop(error);
            }
        };
        window.addEventListener("beforeunload", handleUnloadEvent);
        window.addEventListener("pagehide", handleUnloadEvent);
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
