import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";
import { Macro } from "@web/core/macro";
import { browser } from "@web/core/browser/browser";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import * as hoot from "@odoo/hoot-dom";

export class TourAutomatic {
    mode = "auto";
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

    start() {
        setupEventActions(document.createElement("div"), { allowSubmit: true });
        const { delayToCheckUndeterminisms, stepDelay } = this.config;
        const macroSteps = this.steps
            .filter((step) => step.index >= this.currentIndex)
            .flatMap((step) => [
                {
                    action: async () => {
                        if (this.debugMode) {
                            console.groupCollapsed(step.describeMe);
                            console.log(step.stringify);
                            if (step.break) {
                                // eslint-disable-next-line no-debugger
                                debugger;
                            }
                        } else {
                            console.log(step.describeMe);
                        }
                        // This delay is important for making the current set of tour tests pass.
                        // IMPROVEMENT: Find a way to remove this delay.
                        await new Promise((resolve) => requestAnimationFrame(resolve));
                        if (stepDelay > 0) {
                            await hoot.delay(stepDelay);
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
                            await step.checkForUndeterminisms(trigger, delayToCheckUndeterminisms);
                        }
                        const result = await step.doAction();
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
                        return result;
                    },
                },
            ]);

        const end = () => {
            delete window.hoot;
            transitionConfig.disabled = false;
            tourState.clear();
            //No need to catch error yet.
            window.addEventListener(
                "error",
                (ev) => {
                    ev.preventDefault();
                    ev.stopImmediatePropagation();
                },
                true
            );
            window.addEventListener(
                "unhandledrejection",
                (ev) => {
                    ev.preventDefault();
                    ev.stopImmediatePropagation();
                },
                true
            );
        };

        this.macro = new Macro({
            name: this.name,
            checkDelay: this.checkDelay || 200,
            steps: macroSteps,
            onError: (error) => {
                if (error.type === "Timeout") {
                    this.throwError(...this.currentStep.describeWhyIFailed, error.message);
                } else {
                    this.throwError(error.message);
                }
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
    throwError(...args) {
        console.groupEnd();
        tourState.setCurrentTourOnError();
        // console.error notifies the test runner that the tour failed.
        browser.console.error([`FAILED: ${this.currentStep.describeMe}.`, ...args].join("\n"));
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
