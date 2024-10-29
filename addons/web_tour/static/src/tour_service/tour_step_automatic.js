import { browser } from "@web/core/browser/browser";
import { _legacyIsVisible } from "@web/core/utils/ui";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { callWithUnloadCheck } from "./tour_utils";
import { TourHelpers } from "./tour_helpers";
import { TourStep } from "./tour_step";
import { getTag } from "@web/core/utils/xml";

export class TourStepAutomatic extends TourStep {
    skipped = false;
    hasRun = false;
    constructor(data, tour, index) {
        super(data, tour);
        this.index = index;
        this.tourConfig = tourState.getCurrentConfig();
    }

    get describeWhyIFailed() {
        const errors = [];
        if (this.element) {
            errors.push(`Element has been found.`);
            if (this.isUIBlocked) {
                errors.push("ERROR: DOM is blocked by UI.");
            }
            if (!this.elementIsInModal) {
                errors.push(
                    `BUT: It is not allowed to do action on an element that's below a modal.`
                );
            }
            if (!this.elementIsEnabled) {
                errors.push(`BUT: Element is not enabled.`);
            }
        } else {
            errors.push(
                `The cause is that trigger (${this.trigger}) element cannot be found in DOM. TIP: You can use :not(:visible) to force the search for an invisible element.`
            );
        }
        return errors;
    }

    get describeWhyIFailedDetailed() {
        const offset = 3;
        const start = Math.max(this.index - offset, 0);
        const end = Math.min(this.index + offset, this.tour.steps.length - 1);
        const result = [];
        for (let i = start; i <= end; i++) {
            const stepString = new TourStep(this.tour.steps[i]).stringify;
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
     * When return true, macroEngine stops.
     * @returns {Boolean}
     */
    async doAction() {
        clearTimeout(this._timeout);
        let result = false;
        if (!this.skipped) {
            // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
            const actionHelper = new TourHelpers(this.element);

            if (typeof this.run === "function") {
                const willUnload = await callWithUnloadCheck(async () => {
                    await this.tryToDoAction(() =>
                        // `this.anchor` is expected in many `step.run`.
                        this.run.call({ anchor: this.element }, actionHelper)
                    );
                });
                result = willUnload && "will unload";
            } else if (typeof this.run === "string") {
                for (const todo of this.run.split("&&")) {
                    const m = String(todo)
                        .trim()
                        .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                    await this.tryToDoAction(() =>
                        actionHelper[m.groups?.action](m.groups?.arguments)
                    );
                }
            }
        }
        return result;
    }

    /**
     * Each time it returns false, tour engine wait for a mutation
     * to retry to find the trigger.
     * @returns {(HTMLElement|Boolean)}
     */
    findTrigger() {
        if (!this.active) {
            this.skipped = true;
            return true;
        }
        let nodes;
        try {
            nodes = hoot.queryAll(this.trigger);
        } catch (error) {
            this.throwError(`HOOT: ${error.message}`);
        }
        this.element = this.trigger.includes(":visible")
            ? nodes.at(0)
            : nodes.find(_legacyIsVisible);
        return !this.isUIBlocked && this.elementIsEnabled && this.elementIsInModal
            ? this.element
            : false;
    }

    get isUIBlocked() {
        return (
            document.body.classList.contains("o_ui_blocked") || document.querySelector(".o_blockUI")
        );
    }

    get elementIsInModal() {
        if (!this.element) {
            return false;
        }
        if (this.hasAction) {
            const overlays = hoot.queryFirst(".popover, .o-we-command, .o_notification");
            const modal = hoot.queryFirst(".modal:visible:not(.o_inactive_modal):last");
            if (modal && !overlays && !this.trigger.startsWith("body")) {
                return (
                    modal.contains(hoot.getParentFrame(this.element)) ||
                    modal.contains(this.element)
                );
            }
        }
        return true;
    }

    get elementIsEnabled() {
        const isTag = (array) => array.includes(getTag(this.element, true));
        if (!this.element) {
            return false;
        }
        if (this.hasAction) {
            if (isTag(["input", "textarea"])) {
                return hoot.isEditable(this.element);
            } else if (isTag(["button", "select"])) {
                return !this.element.disabled;
            }
        }
        return true;
    }

    get hasAction() {
        return ["string", "function"].includes(typeof this.run) && !this.skipped;
    }

    async log() {
        setupEventActions(document.createElement("div"));
        if (this.tour.debugMode) {
            console.groupCollapsed(this.describeMe);
            console.log(this.stringify);
            console.groupEnd();
        } else {
            console.log(this.describeMe);
        }
        if (this.break && this.tour.debugMode) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
        const timeout = (this.timeout || 10000) + this.tour.stepDelay;
        this._timeout = browser.setTimeout(
            () => this.throwError(`TIMEOUT: The step failed to complete within ${timeout} ms.`),
            timeout
        );
        // This delay is important for making the current set of tour tests pass.
        // IMPROVEMENT: Find a way to remove this delay.
        await new Promise((resolve) => requestAnimationFrame(resolve));
        await new Promise((resolve) => browser.setTimeout(resolve, this.tour.stepDelay));
    }

    /**
     * @param {string} [error]
     */
    throwError(error = "") {
        tourState.setCurrentTourOnError();
        // console.error notifies the test runner that the tour failed.
        const errors = [`FAILED: ${this.describeMe}.`, ...this.describeWhyIFailed, error];
        console.error(errors.filter(Boolean).join("\n"));
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        console.dir(this.describeWhyIFailedDetailed);
        if (this.tour.debugMode) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    async tryToDoAction(action) {
        try {
            await action();
            this.hasRun = true;
        } catch (error) {
            this.throwError(`ERROR IN ACTION: ${error.message}`);
        }
    }

    async waitForPause() {
        if (this.pause && this.tour.debugMode) {
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
    }
}
