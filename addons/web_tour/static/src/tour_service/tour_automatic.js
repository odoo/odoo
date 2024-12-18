import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";
import { Macro } from "@web/core/macro";
import { browser } from "@web/core/browser/browser";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import * as hoot from "@odoo/hoot-dom";

export class TourAutomatic {
    mode = "auto";
    pointer = null;
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map((step, index) => new TourStepAutomatic(step, this, index));
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

    get checkForUndeterminisms() {
        return this.config.delayToCheckUndeterminisms > 0;
    }

    start(pointer) {
        setupEventActions(document.createElement("div"));
        const macroSteps = this.steps
            .filter((step) => step.index >= this.currentIndex)
            .flatMap((step) => {
                return [
                    {
                        action: async () => {
                            if (this.debugMode) {
                                console.groupCollapsed(step.describeMe);
                                console.log(step.stringify);
                            } else {
                                console.log(step.describeMe);
                            }
                            if (step.break && this.debugMode) {
                                // eslint-disable-next-line no-debugger
                                debugger;
                            }
                            // This delay is important for making the current set of tour tests pass.
                            // IMPROVEMENT: Find a way to remove this delay.
                            await new Promise((resolve) => requestAnimationFrame(resolve));
                            if (this.config.stepDelay > 0) {
                                await hoot.delay(this.config.stepDelay);
                            }
                        },
                    },
                    {
                        initialDelay: () => {
                            return this.previousStepIsJustACheck ? 0 : null;
                        },
                        trigger: () => step.findTrigger(),
                        timeout: (step.timeout || 10000) + this.config.stepDelay,
                        action: async () => {
                            if (this.checkForUndeterminisms) {
                                try {
                                    await step.checkForUndeterminisms();
                                } catch (error) {
                                    this.throwError([
                                        ...this.currentStep.describeWhyIFailed,
                                        error.message,
                                    ]);
                                }
                            }
                            this.previousStepIsJustACheck = !this.currentStep.hasAction;
                            if (this.debugMode) {
                                if (!step.skipped && this.showPointerDuration > 0 && step.element) {
                                    // Useful in watch mode.
                                    pointer.pointTo(step.element, this);
                                    await hoot.delay(this.showPointerDuration);
                                    pointer.hide();
                                }
                                console.log(step.element);
                                if (step.skipped) {
                                    console.log("This step has been skipped");
                                } else {
                                    console.log("This step has run successfully");
                                }
                                console.groupEnd();
                            }
                            const result = await step.doAction();
                            if (step.pause && this.debugMode) {
                                await this.pause();
                            }
                            tourState.setCurrentIndex(step.index + 1);
                            return result;
                        },
                    },
                ];
            });

        const end = () => {
            delete window.hoot;
            transitionConfig.disabled = false;
            tourState.clear();
            pointer.stop();
            //No need to catch error yet.
            window.addEventListener("error", (ev) => ev.preventDefault());
            window.addEventListener("unhandledrejection", (ev) => ev.preventDefault());
        };

        this.macro = new Macro({
            name: this.name,
            checkDelay: this.checkDelay || 300,
            steps: macroSteps,
            onError: (error) => {
                this.throwError([error]);
                end();
            },
            onComplete: () => {
                browser.console.log("tour succeeded");
                // Used to see easily in the python console and to know which tour has been succeeded in suite tours case.
                const succeeded = `║ TOUR ${this.name} SUCCEEDED ║`;
                const msg = [succeeded];
                msg.unshift("╔" + "═".repeat(succeeded.length - 2) + "╗");
                msg.push("╚" + "═".repeat(succeeded.length - 2) + "╝");
                browser.console.log(`\n\n${msg.join("\n")}\n`);
                end();
            },
            onTimeout: (timeout) => {
                this.throwError([
                    ...this.currentStep.describeWhyIFailed,
                    `TIMEOUT: The step failed to complete within ${timeout} ms.`,
                ]);
                end();
            },
        });
        if (this.debugMode && this.currentIndex === 0) {
            // Starts the tour with a debugger to allow you to choose devtools configuration.
            // eslint-disable-next-line no-debugger
            debugger;
        }
        transitionConfig.disabled = true;
        window.hoot = hoot;
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

    /**
     * @param {string} [error]
     */
    throwError(errors = []) {
        console.groupEnd();
        tourState.setCurrentTourOnError();
        // console.error notifies the test runner that the tour failed.
        browser.console.error([`FAILED: ${this.currentStep.describeMe}.`, ...errors].join("\n"));
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
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
            styles[0]
        );
        await new Promise((resolve) => {
            window.play = () => {
                resolve();
                delete window.play;
            };
        });
    }
}
