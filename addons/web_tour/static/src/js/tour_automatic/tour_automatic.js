import * as hootDom from "@odoo/hoot-dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { browser } from "@web/core/browser/browser";
import { Macro } from "@web/core/macro";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "@web_tour/js/tour_automatic/tour_step_automatic";
import { tourState } from "@web_tour/js/tour_state";

export class TourAutomatic {
    mode = "auto";
    allowUnload = true;
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map((step) => new TourStepAutomatic(step, this.mode));
        this.config = tourState.getCurrentConfig() || {};
    }

    get currentIndex() {
        return tourState.getCurrentIndex();
    }

    get currentStep() {
        return this.steps[this.currentIndex];
    }

    describeStep(step) {
        return `[${this.currentIndex + 1}/${this.steps.length}] Tour ${this.name} → ${step.describeMe}`;
    }

    start() {
        setupEventActions(document.createElement("div"), { allowSubmit: true });
        const macroSteps = this.steps.slice(this.currentIndex).flatMap((step) => [
            {
                action: () => {
                    if (this.config.debug) {
                        console.groupCollapsed(this.describeStep(step));
                        console.log(step.stringify);
                    } else {
                        console.log(this.describeStep(step));
                    }
                },
            },
            {
                trigger: step.trigger ? () => step.findTrigger() : null,
                timeout: step.timeout || this.timeout || 10000,
                action: async (trigger) => {
                    this.allowUnload = false;
                    if (!step.skipped && step.expectUnloadPage) {
                        this.allowUnload = true;
                        setTimeout(() => {
                            const message = `
                                    The key { expectUnloadPage } is defined but page has not been unloaded within 20000 ms.
                                    You probably don't need it.
                                `.replace(/^\s+/gm, "");
                            this.throwError(message);
                        }, 20000);
                    }

                    await step.doAction();
                    tourState.setCurrentIndex(this.currentIndex + 1);
                    if (this.config.debug) {
                        console.log(trigger);
                        console.groupEnd();
                    }
                    if (this.allowUnload || this.config.debug) {
                        return "StopTheMacro!";
                    }
                },
            },
        ]);

        this.macro = new Macro({
            name: this.name,
            steps: macroSteps,
            allowDelayToRemove: this.config.allowDelayToRemove,
            onError: ({ error }) => {
                if (error.type === "Timeout") {
                    this.throwError(...this.currentStep.describeWhyIFailed, error.message);
                } else {
                    this.throwError(error.message);
                }
                this.end();
            },
            onComplete: () => {
                browser.console.log("tour succeeded");
                // Used to see easily in the python console and to know which tour has been succeeded in suite tours case.
                const succeeded = `║ TOUR ${this.name} SUCCEEDED ║`;
                const msg = [succeeded];
                msg.unshift("╔" + "═".repeat(succeeded.length - 2) + "╗");
                msg.push("╚" + "═".repeat(succeeded.length - 2) + "╝");
                browser.console.log(`\n\n${msg.join("\n")}\n`);
                this.end();
            },
        });

        const beforeUnloadHandler = (ev) => {
            if (!this.allowUnload && tourState.getCurrentTour()) {
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

        transitionConfig.disabled = true;
        this.hootNameSpace = hootDom.exposeHelpers(hootDom);
        console.debug(`Hoot DOM helpers available from \`window.${this.hootNameSpace}\``);
        if (!this.config.debug) {
            this.macro.start();
        }
    }

    end() {
        if (this.hootNameSpace) {
            delete window[this.hootNameSpace];
        }
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
                const failing_step = `${line} FAILED: ${this.describeStep(step)} ${line}`;
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
        tourState.setCurrentTourOnError();
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        browser.console.dir(this.describeWhereIFailed);
        if (!this.config.debug) {
            const error = [`FAILED: ${this.describeStep(this.currentStep)}.`, ...args].join("\n");
            // console.error notifies the test runner that the tour failed.
            browser.console.error(error);
        }
    }
}
