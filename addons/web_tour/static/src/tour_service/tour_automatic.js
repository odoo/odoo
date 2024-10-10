import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";
import { browser } from "@web/core/browser/browser";
import { Mutex } from "@web/core/utils/concurrency";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { MacroMutationObserver } from "@web/core/macro";
import * as hoot from "@odoo/hoot-dom";

const mutex = new Mutex();

export class TourAutomatic {
    isComplete = false;
    isErrored = false;
    mode = "auto";
    previousStepIsJustACheck = false;
    timer = null;
    constructor(data) {
        Object.assign(this, data);
        this.debounceDelay = Math.max(this.checkDelay || 500, 50);
        this.steps = this.steps.map((step, index) => new TourStepAutomatic(step, this, index));
        this.stepDelay = parseInt(tourState.getCurrentConfig().stepDelay) || 0;
        this.stepElFound = new Array(this.steps.length).fill(false);
        this.stepHasStarted = new Array(this.steps.length).fill(false);
        this.observer = new MacroMutationObserver(() => this.continue("mutation"));
        this.delayToCheckUndeterminisms =
            (parseInt(tourState.getCurrentConfig().delayToCheckUndeterminisms) || 0) * 1000;
        if (this.delayToCheckUndeterminisms > 0) {
            browser.console.warn(`The tour ${this.name} is run in checkForUndeterminisms mode`);
        }
    }

    /**
     * @returns {TourStepAutomatic}
     */
    get currentStep() {
        return this.steps[this.currentIndex];
    }

    get debugMode() {
        const config = tourState.getCurrentConfig() || {};
        return config.debug !== false;
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

    /**
     * Add a debugger to the tour at the current step
     */
    break() {
        if (this.debugMode && this.currentStep.break) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    async checkForUndeterminisms() {
        if (this.delayToCheckUndeterminisms > 0) {
            await new Promise((resolve) => {
                browser.setTimeout(() => {
                    const stepEl = this.currentStep.findTrigger();
                    if (this.stepElFound[this.currentIndex] === stepEl) {
                        resolve();
                    } else {
                        this.throwError([
                            `UNDETERMINISTIC: two differents elements has been found in ${this.delayToCheckUndeterminisms}ms for trigger ${this.currentStep.trigger}`,
                        ]);
                    }
                }, this.delayToCheckUndeterminisms);
            });
        }
    }

    clearTimeout() {
        if (this.timeout) {
            browser.clearTimeout(this.timeout);
        }
    }

    clearTimer() {
        this.clearTimeout();
        if (this.timer) {
            browser.clearTimeout(this.timer);
        }
    }

    /**
     * @description Adding the current step in tour queue (via mutex)
     * From "next" can only be called once per step.
     * From "mutation" can be called multiple times per step.
     *      Each time it is called, if the delay is not reached,
     *      the timeout is overwritten (we wait for the DOM to stabilize)
     * When a findTrigger is fired, we search the DOM for the element synchronously.
     * Once it is found, we prevent incoming mutations from overwriting
     * the current step. We do the step's action, move on to the
     * next step, and take the mutations into account again.
     * @param {"mutation"|"next"} from
     */
    continue(from) {
        if (this.isComplete) {
            return;
        }
        if (from === "next" && this.stepHasStarted[this.currentIndex]) {
            return;
        }
        let delay = this.debounceDelay;
        // Called once per step.
        if (!this.stepHasStarted[this.currentIndex]) {
            this.log();
            this.break();
            this.setTimer();
            delay = 150;
            if (this.previousStepIsJustACheck) {
                delay = 0;
            }
            this.stepHasStarted[this.currentIndex] = from;
        }
        this.setTimeout(delay);
    }

    async consumeCurrentStep() {
        // FIND TRIGGER
        let stepEl = null;
        try {
            stepEl = this.currentStep.findTrigger();
        } catch (error) {
            this.throwError([`Try to find trigger: ${error.message}`]);
        }
        // RUN ACTION
        if (stepEl) {
            this.stepElFound[this.currentIndex] = stepEl;
            this.previousStepIsJustACheck = !this.currentStep.hasAction;
            this.clearTimer();
            await this.checkForUndeterminisms();
            if (this.debugMode && stepEl !== true) {
                this.pointer.pointTo(stepEl, this);
            }
            let actionResult = null;
            try {
                actionResult = await this.currentStep.doAction();
            } catch (error) {
                this.throwError([`Try to run: ${error.message}`]);
            }
            await this.pause();
            this.increment();
            if (!actionResult) {
                await this.waitDelay();
                this.continue("next");
            }
        }
    }

    increment() {
        this.currentIndex++;
        if (this.currentIndex === this.steps.length) {
            this.stop();
        }
        tourState.setCurrentIndex(this.currentIndex);
    }

    log() {
        browser.console.groupCollapsed(this.currentStep.describeMe);
        if (this.debugMode) {
            console.log(this.currentStep.stringify);
        }
        browser.console.groupEnd();
    }

    /**
     * Pause the tour at current step
     */
    async pause() {
        if (!this.isComplete && this.currentStep.pause && this.debugMode) {
            const styles = [
                "background: black; color: white; font-size: 14px",
                "background: black; color: orange; font-size: 14px",
            ];
            browser.console.log(
                `%cTour is paused. Use %cplay()%c to continue.`,
                styles[0],
                styles[1],
                styles[0]
            );
            await new Promise((resolve) => {
                window.hoot = hoot;
                window.play = () => {
                    delete window.hoot;
                    delete window.play;
                    resolve();
                };
            });
        }
    }

    /** Debounce at start of the current step and each mutation.
     */
    setTimeout(delay) {
        this.clearTimeout();
        if (!this.stepElFound[this.currentIndex]) {
            this.timeout = browser.setTimeout(() => {
                mutex.exec(() => this.consumeCurrentStep());
            }, delay);
        }
    }

    /** Set timer for the current step.
     * At the end of timer, the current step fails.
     */
    setTimer() {
        const timeout = this.currentStep.timeout || 10000;
        this.timer = browser.setTimeout(() => {
            this.throwError([
                `TIMEOUT: This step cannot be succeeded within ${timeout}ms.`,
                ...this.currentStep.describeWhyFailed,
            ]);
        }, timeout);
    }

    start(pointer, callback) {
        this.callback = callback;
        this.pointer = pointer;
        setupEventActions(document.createElement("div"));
        transitionConfig.disabled = true;
        this.currentIndex = tourState.getCurrentIndex();
        if (this.debugMode && this.currentIndex === 0) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
        this.observer.observe(document.body);
        this.continue("next");
    }

    stop() {
        transitionConfig.disabled = false;
        this.observer.disconnect();
        if (!this.isComplete) {
            this.isComplete = true;
            tourState.clear();
            if (!this.isErrored) {
                // Used to signal the python test runner that the tour finished without error.
                browser.console.log(`tour succeeded`);
                // Used to see easily in the python console and to know which tour has been succeeded in suite tours case.
                const succeeded = `║ TOUR ${this.name} SUCCEEDED ║`;
                const msg = [succeeded];
                msg.unshift("╔" + "═".repeat(succeeded.length - 2) + "╗");
                msg.push("╚" + "═".repeat(succeeded.length - 2) + "╝");
                browser.console.log(`\n\n${msg.join("\n")}\n`);
            } else {
                browser.console.error(`tour ${this.name} not succeeded`);
            }
            this.callback();
        }
        return;
    }

    /**
     * @param {string} [error]
     */
    throwError(errors = []) {
        this.isErrored = true;
        tourState.setCurrentTourOnError();
        // console.error notifies the test runner that the tour failed.
        errors.unshift(`FAILED: ${this.currentStep.describeMe}.`);
        browser.console.error(errors.join("\n"));
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        browser.console.dir(this.describeWhereIFailed);
        this.stop();
        if (this.debugMode) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    async waitDelay() {
        if (this.stepDelay) {
            await new Promise((resolve) => browser.setTimeout(resolve, this.stepDelay));
        }
    }
}
