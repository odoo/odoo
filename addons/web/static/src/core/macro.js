import { assertType, t } from "@odoo/owl";
import { isVisible } from "@web/core/utils/ui";
import { delay } from "@web/core/utils/concurrency";

const macroSchema = t.strictObject({
    name: t.string().optional(),
    timeout: t.number().optional(),
    allowDelayToRemove: t.boolean().optional(),
    steps: t.array(
        t.customValidator(
            t.object({
                action: t.or([t.function(), t.string()]).optional(),
                timeout: t.number().optional(),
                trigger: t.or([t.function(), t.string()]).optional(),
            }),
            (step) => step.action || step.trigger
        )
    ),
    onComplete: t.function().optional(),
    onStep: t.function().optional(),
    onError: t.function().optional(),
});

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
            { cause: error }
        );
    }
}

async function waitForTrigger(trigger, waitDelay = false) {
    if (!trigger) {
        return;
    }
    try {
        if (waitDelay) {
            await delay(50);
        }
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
            assertType(descr, macroSchema);
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
                // To be remove ASAP because it allows non deterministic behaviors.
                const trigger = await waitForTrigger(step.trigger, this.allowDelayToRemove);
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
