import { browser } from "@web/core/browser/browser";
import { _legacyIsVisible } from "@web/core/utils/ui";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { callWithUnloadCheck } from "./tour_utils";
import { TourHelpers } from "./tour_helpers";
import { TourStep } from "./tour_step";
import { pick } from "@web/core/utils/objects";

export class TourStepAutomatic extends TourStep {
    triggerFound = false;
    hasRun = false;
    isBlocked = false;
    running = false;
    constructor(data, tour, index) {
        super(data, tour);
        this.index = index;
    }

    get canContinue() {
        this.isBlocked =
            document.body.classList.contains("o_ui_blocked") ||
            document.querySelector(".o_blockUI");
        return !this.isBlocked;
    }

    /**
     * @type {TourStepCompiler}
     * @param {TourStep} step
     * @param {object} options
     * @returns {{trigger, action}[]}
     */
    compileToMacro(pointer) {
        const debugMode = tourState.get(this.tour.name, "debug");

        return [
            {
                action: async () => {
                    this.running = true;
                    console.log(this.describeMe);
                    setupEventActions(document.createElement("div"));
                    // This delay is important for making the current set of tour tests pass.
                    // IMPROVEMENT: Find a way to remove this delay.
                    await new Promise((resolve) => requestAnimationFrame(resolve));
                    await new Promise((resolve) =>
                        browser.setTimeout(resolve, this.tour.stepDelay)
                    );
                },
            },
            {
                trigger: async () => {
                    if (!this.active) {
                        this.run = () => {};
                        return true;
                    }
                    return await this.findTrigger();
                },
                action: async (stepEl) => {
                    tourState.set(this.tour.name, "currentIndex", this.index + 1);
                    if (this.tour.showPointerDuration > 0 && stepEl !== true) {
                        // Useful in watch mode.
                        pointer.pointTo(stepEl, this);
                        await new Promise((r) =>
                            browser.setTimeout(r, this.tour.showPointerDuration)
                        );
                        pointer.hide();
                    }

                    if (this.break && debugMode !== false) {
                        // eslint-disable-next-line no-debugger
                        debugger;
                    }

                    return this.tryToDoAction(stepEl);
                },
            },
            {
                action: async () => {
                    if (this.pause && debugMode !== false) {
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
                    this.running = false;
                },
            },
        ];
    }

    get describeWhyIFailed() {
        if (!this.triggerFound) {
            return `The cause is that trigger (${this.trigger}) element cannot be found in DOM. TIP: You can use :not(:visible) to force the search for an invisible element.`;
        } else if (this.isBlocked) {
            return "Element has been found but DOM is blocked by UI.";
        } else if (!this.hasRun) {
            return `Element has been found. The error seems to be with step.run`;
        }
        return "";
    }

    get describeWhyIFailedDetailed() {
        const offset = 3;
        const start = Math.max(this.index - offset, 0);
        const end = Math.min(this.index + offset, this.tour.steps.length - 1);
        const result = [];
        for (let i = start; i <= end; i++) {
            const stepString =
                JSON.stringify(
                    pick(
                        this.tour.steps[i],
                        "isActive",
                        "content",
                        "trigger",
                        "run",
                        "tooltipPosition",
                        "timeout"
                    ),
                    (_key, value) => {
                        if (typeof value === "function") {
                            return "[function]";
                        } else {
                            return value;
                        }
                    },
                    2
                ) + ",";
            const text = [stepString];
            if (i === this.index) {
                const line = "-".repeat(10);
                const failing_step = `${line} FAILED: ${this.describeMe} ${line}`;
                text.unshift(failing_step);
                text.push("-".repeat(failing_step.length));
            }
            result.push(...text);
        }
        return result.join("\n");
    }

    /**
     * @returns {HTMLElement}
     */
    async findTrigger() {
        const timeout = (this.timeout || 20000) + this.tour.stepDelay;
        return hoot.waitUntil(
            () => {
                const nodes = hoot.queryAll(this.trigger);
                const triggerEl = this.trigger.includes(":visible")
                    ? nodes.at(0)
                    : nodes.find(_legacyIsVisible);
                if (this.canContinue) {
                    this.triggerFound = !!triggerEl;
                    return triggerEl;
                }
            },
            {
                timeout,
                message: () => {
                    this.throwError();
                    return "Trigger not found";
                },
            }
        );
    }

    /**
     * @param {Array<string>} [errors]
     */
    throwError(error = "") {
        tourState.set(this.tour.name, "stepState", "errored");
        const debugMode = tourState.get(this.tour.name, "debug");
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        console.warn(this.describeWhyIFailedDetailed);
        // console.error notifies the test runner that the tour failed.
        console.error(`FAILED: ${this.describeMe}. ${this.describeWhyIFailed}`);
        if (error.length) {
            console.error(error);
        }
        if (debugMode !== false) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    async tryToDoAction(stepEl) {
        const timeout = 500;
        if (!["function", "string"].includes(typeof this.run)) {
            return;
        }
        try {
            let result;
            const actionHelper = new TourHelpers(stepEl);
            // await new Promise((r) => setTimeout(r, 400));
            if (typeof this.run === "function") {
                await new Promise((resolve) => setTimeout(resolve, timeout));
                const willUnload = await callWithUnloadCheck(async () => {
                    await this.run.call({ anchor: stepEl }, actionHelper);
                });
                result = willUnload && "will unload";
            } else if (typeof this.run === "string") {
                for (const todo of this.run.split("&&")) {
                    const m = String(todo)
                        .trim()
                        .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                    await new Promise((resolve) => setTimeout(resolve, timeout));
                    await actionHelper[m.groups?.action](m.groups?.arguments);
                }
            }
            this.hasRun = true;
            return result;
        } catch (error) {
            this.throwError(error.message);
        }
    }
}
