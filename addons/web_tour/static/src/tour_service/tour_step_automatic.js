import { browser } from "@web/core/browser/browser";
import { _legacyIsVisible } from "@web/core/utils/ui";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { callWithUnloadCheck } from "./tour_utils";
import { TourHelpers } from "./tour_helpers";
import { TourStep } from "./tour_step";

export class TourStepAutomatic extends TourStep {
    triggerFound = false;
    hasRun = false;
    isBlocked = false;
    running = false;
    constructor(data, tour, index) {
        super(data, tour);
        this.index = index;
        this.tourConfig = tourState.getCurrentConfig();
    }

    get describeWhyIFailed() {
        if (!this.triggerFound) {
            return `The cause is that trigger (${this.trigger}) element cannot be found in DOM. TIP: You can use :not(:visible) to force the search for an invisible element.`;
        } else if (this.isBlocked) {
            return "Element has been found but DOM is blocked by UI.";
        } else if (this.hasModal) {
            return `Element has been found but it's not allowed to do action on an element that's below a modal.`;
        } else if (!this.hasRun) {
            return `Element has been found. The error seems to be with step.run.`;
        }
        return "";
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

    async doAction(stepEl) {
        clearTimeout(this._timeout);
        tourState.setCurrentIndex(this.index + 1);
        if (this.tour.showPointerDuration > 0 && stepEl !== true) {
            // Useful in watch mode.
            this.tour.pointer.pointTo(stepEl, this);
            await new Promise((r) => browser.setTimeout(r, this.tour.showPointerDuration));
            this.tour.pointer.hide();
        }

        // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
        const actionHelper = new TourHelpers(stepEl);

        let result;
        if (typeof this.run === "function") {
            const willUnload = await callWithUnloadCheck(async () => {
                await this.tryToDoAction(() =>
                    // `this.anchor` is expected in many `step.run`.
                    this.run.call({ anchor: stepEl }, actionHelper)
                );
            });
            result = willUnload && "will unload";
        } else if (typeof this.run === "string") {
            for (const todo of this.run.split("&&")) {
                const m = String(todo)
                    .trim()
                    .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                await this.tryToDoAction(() => actionHelper[m.groups?.action](m.groups?.arguments));
            }
        }
        return result;
    }

    /**
     * @returns {HTMLElement}
     */
    findTrigger() {
        if (!this.active) {
            this.run = () => {};
            return true;
        }
        let nodes;
        try {
            nodes = hoot.queryAll(this.trigger);
        } catch (error) {
            this.throwError(`Trigger was not found : ${this.trigger} : ${error.message}`);
        }
        const triggerEl = this.trigger.includes(":visible")
            ? nodes.at(0)
            : nodes.find(_legacyIsVisible);
        this.triggerFound = !!triggerEl;
        this.isBlocked =
            document.body.classList.contains("o_ui_blocked") ||
            document.querySelector(".o_blockUI");
        if (!this.isBlocked) {
            if (triggerEl && this.hasAction) {
                const overlays = hoot.queryFirst(".popover, .o-we-command, .o_notification");
                this.hasModal = hoot.queryFirst(".modal:visible:not(.o_inactive_modal):last");
                if (this.hasModal && !overlays && !this.trigger.startsWith("body")) {
                    return this.hasModal.contains(hoot.getParentFrame(triggerEl)) ||
                        this.hasModal.contains(triggerEl)
                        ? triggerEl
                        : false;
                }
            }
            return triggerEl;
        }
        return false;
    }

    get hasAction() {
        return ["string", "function"].includes(typeof this.run);
    }

    async log() {
        this.running = true;
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
        this._timeout = browser.setTimeout(
            () => this.throwError(),
            (this.timeout || 10000) + this.tour.stepDelay
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
        const tourConfig = tourState.getCurrentConfig();
        // console.error notifies the test runner that the tour failed.
        const errors = [`FAILED: ${this.describeMe}.`, this.describeWhyIFailed, error];
        console.error(errors.filter(Boolean).join("\n"));
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        console.dir(this.describeWhyIFailedDetailed);
        if (tourConfig.debug !== false) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    async tryToDoAction(action) {
        try {
            await action();
            this.hasRun = true;
        } catch (error) {
            this.throwError(error.message);
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
