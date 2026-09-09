/** @odoo-module native */
/* eslint-disable no-console -- automated tour runner; step-progress output to console is its purpose */
import hootDom from "@odoo/hoot-dom";
import { enableEventLogs, setupEventActions } from "@odoo/hoot-dom-helpers-events";
import { browser } from "@web/core/browser/browser";
import { RpcEvent } from "@web/core/events";
import { rpcBus } from "@web/core/network";
import { config as transitionConfig } from "@web/core/transition";
import { Macro } from "@web/core/utils/macro";
import { TourStepAutomatic } from "@web_tour/js/tour_automatic/tour_step_automatic";
import { tourState } from "@web_tour/js/tour_state";

const CLIENT_SETTLE_TIMEOUT = 10000;
const EXPIRED = Symbol("expired");
const SETTLED = Symbol("settled");

/**
 * Silence errors raised after a tour has finished, and un-silence them when
 * the next one starts.
 *
 * `end()` used to install this pair as two inline arrows, which nothing could
 * remove afterwards -- no reference to them existed. Every finished automatic
 * tour therefore left another capturing `error`/`unhandledrejection` listener
 * behind for the lifetime of the page, each one calling
 * `stopImmediatePropagation()`, so a second tour in the same page ran blind
 * and any handler registered *after* a finished tour (a later test's own error
 * assertion, an error reporter mounted after an onboarding tour) could have
 * its detection eaten by a leftover. There is exactly one pair now, and it
 * only lives between the end of one tour and the start of the next.
 *
 * A named function also makes the install idempotent on its own:
 * `addEventListener` drops a duplicate (same target, type, callback, capture).
 * The flag is kept so removal is symmetric and cheap to reason about.
 */
const swallowError = (ev) => {
    ev.preventDefault();
    ev.stopImmediatePropagation();
};
let postTourErrorsSwallowed = false;

function swallowPostTourErrors() {
    if (postTourErrorsSwallowed) {
        return;
    }
    window.addEventListener("error", swallowError, true);
    window.addEventListener("unhandledrejection", swallowError, true);
    postTourErrorsSwallowed = true;
}

function stopSwallowingPostTourErrors() {
    if (!postTourErrorsSwallowed) {
        return;
    }
    window.removeEventListener("error", swallowError, true);
    window.removeEventListener("unhandledrejection", swallowError, true);
    postTourErrorsSwallowed = false;
}

export class TourAutomatic {
    mode = "auto";
    allowUnload = true;
    unloadWatchdog = null;
    pendingRPCs = new Set();
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map(
            (step, index) => new TourStepAutomatic(step, this, index),
        );
        this.config = tourState.getCurrentConfig() || {};
    }

    get currentIndex() {
        return tourState.getCurrentIndex();
    }

    get currentStep() {
        return this.steps[this.currentIndex];
    }

    get debugMode() {
        return this.config.debug !== false;
    }

    async whenClientSettles(timeout = CLIENT_SETTLE_TIMEOUT) {
        if (!this.pendingRPCs.size) {
            return true;
        }
        let onExpire;
        const expired = new Promise((resolve) => {
            onExpire = () => resolve(EXPIRED);
        });
        const timer = browser.setTimeout(onExpire, timeout);
        const listeners = [];
        try {
            while (true) {
                if (!this.pendingRPCs.size) {
                    const frame = new Promise((resolve) =>
                        browser.requestAnimationFrame(() => resolve(SETTLED)),
                    );
                    if ((await Promise.race([frame, expired])) === EXPIRED) {
                        break;
                    }
                    if (!this.pendingRPCs.size) {
                        return true;
                    }
                    continue;
                }
                const answered = new Promise((resolve) => {
                    const done = () => resolve(SETTLED);
                    listeners.push(done);
                    rpcBus.addEventListener(RpcEvent.RESPONSE, done);
                });
                if ((await Promise.race([answered, expired])) === EXPIRED) {
                    break;
                }
            }
        } finally {
            browser.clearTimeout(timer);
            for (const done of listeners) {
                rpcBus.removeEventListener(RpcEvent.RESPONSE, done);
            }
        }
        this.pendingRPCs.clear();
        return false;
    }

    start() {
        // Whatever the tour before this one left silenced, this one needs to
        // see.
        stopSwallowingPostTourErrors();
        setupEventActions(document.createElement("div"), { allowSubmit: true });
        enableEventLogs(this.debugMode);
        const onRPCRequest = (ev) => this.pendingRPCs.add(ev.detail.data.id);
        const onRPCResponse = (ev) => this.pendingRPCs.delete(ev.detail?.data?.id);
        rpcBus.addEventListener(RpcEvent.REQUEST, onRPCRequest);
        rpcBus.addEventListener(RpcEvent.RESPONSE, onRPCResponse);
        const { delayToCheckUndeterminisms, stepDelay } = this.config;
        const macroSteps = this.steps
            .filter((step) => step.index >= this.currentIndex)
            .flatMap((step) => [
                {
                    action: async () => {
                        if (this.debugMode) {
                            console.groupCollapsed(step.describeMe);
                            console.log(step.stringify);
                            if (stepDelay > 0) {
                                await hootDom.delay(stepDelay);
                            }
                            if (step.break) {
                                // eslint-disable-next-line no-debugger
                                debugger;
                            }
                        } else {
                            console.log(step.describeMe);
                        }
                        // a step that only observes may catch a state that
                        // exists while requests are in flight (a loading
                        // screen); only acting waits for the client to settle
                        if (!step.expectUnloadPage && step.hasAction) {
                            await this.whenClientSettles();
                        }
                    },
                },
                {
                    trigger: step.trigger ? () => step.findTrigger() : null,
                    timeout:
                        step.pause && this.debugMode
                            ? 9999999
                            : step.timeout || this.timeout || 10000,
                    action: async (trigger) => {
                        if (delayToCheckUndeterminisms > 0) {
                            await step.checkForUndeterminisms(
                                trigger,
                                delayToCheckUndeterminisms,
                            );
                        }
                        this.allowUnload = false;
                        if (!step.skipped && step.expectUnloadPage) {
                            this.allowUnload = true;
                            browser.clearTimeout(this.unloadWatchdog);
                            this.unloadWatchdog = browser.setTimeout(() => {
                                const message = `
                                    The key { expectUnloadPage } is defined but page has not been unloaded within 20000 ms.
                                    You probably don't need it.
                                `.replace(/^\s+/gm, "");
                                this.throwError(message);
                            }, 20000);
                        }
                        await step.doAction();
                        if (!this.allowUnload) {
                            await new Promise((resolve) =>
                                browser.requestAnimationFrame(resolve),
                            );
                        }
                        if (this.debugMode) {
                            console.log(trigger);
                            if (step.skipped) {
                                console.log("This step has been skipped");
                            } else {
                                console.log("This step has run successfully");
                            }
                            console.groupEnd();
                            if (step.pause) {
                                await this.pause();
                            }
                        }
                        tourState.setCurrentIndex(step.index + 1);
                        if (this.allowUnload) {
                            return Macro.STOP;
                        }
                    },
                },
            ]);

        const end = () => {
            rpcBus.removeEventListener(RpcEvent.REQUEST, onRPCRequest);
            rpcBus.removeEventListener(RpcEvent.RESPONSE, onRPCResponse);
            this.pendingRPCs.clear();
            browser.clearTimeout(this.unloadWatchdog);
            this.unloadWatchdog = null;
            delete window[hootNameSpace];
            transitionConfig.disabled = false;
            tourState.clear();
            // The tour is over: an error the page raises from here on belongs
            // to nobody and must not fail a run that already reported its
            // result. Owned by the module rather than by this closure -- see
            // `swallowPostTourErrors`.
            swallowPostTourErrors();
        };

        this.macro = new Macro({
            name: this.name,
            steps: macroSteps,
            onError: ({ error }) => {
                if (error.type === "Timeout") {
                    this.throwError(
                        ...this.currentStep.describeWhyIFailed,
                        error.message,
                    );
                } else {
                    this.throwError(error.message);
                }
                end();
            },
            onComplete: async () => {
                // a tour is over when the client is idle: the last steps
                // only observed, and what they observed may still be saving,
                // which the harness would then report as a dirty form
                await this.whenClientSettles();
                browser.console.log("tour succeeded");
                const succeeded = `║ TOUR ${this.name} SUCCEEDED ║`;
                const msg = [succeeded];
                msg.unshift("╔" + "═".repeat(succeeded.length - 2) + "╗");
                msg.push("╚" + "═".repeat(succeeded.length - 2) + "╝");
                browser.console.log(`\n\n${msg.join("\n")}\n`);
                end();
            },
        });

        const beforeUnloadHandler = () => {
            if (!this.allowUnload) {
                const message = `
                    Be sure to use { expectUnloadPage: true } for any step
                    that involves firing a beforeUnload event.
                    This avoid a non-deterministic behavior by explicitly stopping
                    the tour that might continue before the page is unloaded.
                `.replace(/^\s+/gm, "");
                this.throwError(message);
            }
        };
        window.addEventListener("beforeunload", beforeUnloadHandler);

        if (this.debugMode && this.currentIndex === 0) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
        transitionConfig.disabled = true;
        const hootNameSpace = hootDom.exposeHelpers(hootDom);
        console.debug(`Hoot DOM helpers available from \`window.${hootNameSpace}\``);
        this.macro.start();
    }

    get describeWhereIFailed() {
        const offset = 3;
        const start = Math.max(this.currentIndex - offset, 0);
        const end = Math.min(this.currentIndex + offset, this.steps.length - 1);
        const result = [];
        for (let i = start; i <= end; i++) {
            const step = this.steps[i];
            const stepString = step.stringify;
            const text = [stepString];
            if (i === this.currentIndex) {
                const line = "-".repeat(10);
                const failing_step = `${line} FAILED: ${step.describeMe} ${line}`;
                text.unshift(failing_step);
                text.push("-".repeat(failing_step.length));
            }
            result.push(...text);
        }
        return result.join("\n");
    }

    /** @param {string} [error] */
    throwError(...args) {
        console.groupEnd();
        tourState.setCurrentTourOnError();
        const step = this.currentStep;
        const failed = step
            ? `FAILED: ${step.describeMe}.`
            : `FAILED: after the last step ran (index ${this.currentIndex} of ${this.steps.length}).`;
        browser.console.error([failed, ...args].join("\n"));
        browser.console.dir(this.describeWhereIFailed);
        if (this.debugMode) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    async pause() {
        const styles = [
            "background: black; color: white; font-size: 14px",
            "background: black; color: orange; font-size: 14px",
        ];
        console.log(
            `%cTour is paused. Use %cplay()%c to continue.`,
            styles[0],
            styles[1],
            styles[0],
        );
        await new Promise((resolve) => {
            window.play = () => {
                resolve();
                delete window.play;
            };
        });
    }
}
