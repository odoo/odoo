import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";
import { MacroEngine } from "@web/core/macro";
import { browser } from "@web/core/browser/browser";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";

export class TourAutomatic {
    mode = "auto";
    paused = false;
    pointer = null;
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map((step, index) => new TourStepAutomatic(step, this, index));
        this.macroEngine = new MacroEngine({
            target: document,
            defaultCheckDelay: 500,
        });
        const tourConfig = tourState.getCurrentConfig();
        this.stepDelay = tourConfig.stepDelay;
    }

    get currentIndex() {
        return tourState.getCurrentIndex();
    }

    get currentStep() {
        return this.steps[this.currentIndex];
    }

    get debugMode() {
        const tourConfig = tourState.getCurrentConfig() || {};
        return tourConfig.debug !== false;
    }

    start(pointer) {
        const macroSteps = this.steps
            .filter((step) => step.index >= this.currentIndex)
            .flatMap((step) => {
                const timeout = (step.timeout || 10000) + this.stepDelay;
                return [
                    {
                        action: async () => {
                            await this.pause();
                            setupEventActions(document.createElement("div"));
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
                            await new Promise((resolve) =>
                                browser.setTimeout(resolve, this.stepDelay)
                            );
                        },
                    },
                    {
                        trigger: () => step.findTrigger(),
                        timeout,
                        onTimeout: () => {
                            this.throwError(
                                `TIMEOUT: The step failed to complete within ${timeout} ms.`
                            );
                        },
                        action: async () => {
                            if (this.debugMode) {
                                this.paused = step.pause;
                                if (!step.skipped && this.showPointerDuration > 0 && step.element) {
                                    // Useful in watch mode.
                                    pointer.pointTo(step.element, this);
                                    await new Promise((r) =>
                                        browser.setTimeout(r, this.showPointerDuration)
                                    );
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
                            tourState.setCurrentIndex(step.index + 1);
                            return result;
                        },
                    },
                ];
            });

        const end = () => {
            transitionConfig.disabled = false;
            tourState.clear();
            pointer.stop();
        };

        const macro = {
            name: this.name,
            checkDelay: this.checkDelay,
            steps: macroSteps,
            onError: (error) => {
                this.throwError(error);
                console.error("tour not succeeded");
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
        };
        if (this.debugMode) {
            // Starts the tour with a debugger to allow you to choose devtools configuration.
            // eslint-disable-next-line no-debugger
            debugger;
        }
        transitionConfig.disabled = true;
        //Activate macro in exclusive mode (only one macro per MacroEngine)
        this.macroEngine.activate(macro, true);
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
    throwError(error = ``) {
        console.groupEnd();
        tourState.setCurrentTourOnError();
        // console.error notifies the test runner that the tour failed.
        const errors = [
            `FAILED: ${this.currentStep.describeMe}.`,
            ...this.currentStep.describeWhyIFailed,
            error,
        ];
        browser.console.error(errors.filter(Boolean).join("\n"));
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        browser.console.dir(this.describeWhereIFailed);
        if (this.debugMode) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    async pause() {
        if (this.paused) {
            this.paused = false;
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
}
