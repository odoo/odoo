import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { callWithUnloadCheck, serializeChanges } from "./tour_utils";
import { TourHelpers } from "./tour_helpers";
import { TourStep } from "./tour_step";
import { getTag } from "@web/core/utils/xml";

export class TourStepTrigger {
    constructor(trigger, hasAction = false) {
        this.trigger = trigger;
        this.hasAction = hasAction;
    }

    /**
     * @returns {(HTMLElement|Boolean)}
     */
    find() {
        const visible = !/:(hidden|visible)\b/.test(this.trigger);
        this.element = hoot.queryFirst(this.trigger, { visible });
        if (this.element) {
            return !this.isUIBlocked &&
                this.elementIsEnabled &&
                this.elementIsInModal &&
                this.parentFrameIsReady
                ? this.element
                : false;
        }
        return false;
    }

    get isUIBlocked() {
        return (
            document.body.classList.contains("o_ui_blocked") ||
            document.querySelector(".o_blockUI") ||
            document.querySelector(".o_is_blocked")
        );
    }

    get parentFrameIsReady() {
        if (this.trigger.match(/\[is-ready=(true|false)\]/)) {
            return true;
        }
        const parentFrame = hoot.getParentFrame(this.element);
        return parentFrame && parentFrame.hasAttribute("is-ready")
            ? parentFrame.getAttribute("is-ready") === "true"
            : true;
    }

    get elementIsInModal() {
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
        if (this.hasAction) {
            if (isTag(["input", "textarea"])) {
                return hoot.isEditable(this.element);
            } else if (isTag(["button", "select"])) {
                return !this.element.disabled;
            }
        }
        return true;
    }
}

export class TourStepAutomatic extends TourStep {
    skipped = false;
    error = "";
    constructor(data, tour, index) {
        super(data, tour);
        this.index = index;
        this.tourConfig = tourState.getCurrentConfig();
    }

    async waitDelay(triggerBeforeDelay, trigger, delay) {
        if (delay <= 0 || !triggerBeforeDelay || this.skipped) {
            return;
        }
        await new Promise((resolve) => setTimeout(resolve, delay));
        const triggerAfterDelay = await hoot.waitUntil(
            () => new TourStepTrigger(trigger, this.hasAction).find(),
            { timeout: 5000 }
        );
        let reason;
        if (triggerBeforeDelay !== triggerAfterDelay) {
            reason =
                `Initial element has changed:\n` +
                JSON.stringify(serializeChanges(triggerBeforeDelay, triggerAfterDelay), null, 2);
        }
        if (reason) {
            throw new Error(
                `Potential non deterministic behavior found in ${delay}ms for trigger ${this.trigger}.\n${reason}`
            );
        }
    }

    get describeWhyIFailed() {
        const errors = [];
        if (this.element) {
            errors.push(`Element has been found.`);
            if (this.isUIBlocked) {
                errors.push("BUT: DOM is blocked by UI.");
            }
            if (!this.elementIsInModal) {
                errors.push(
                    `BUT: It is not allowed to do action on an element that's below a modal.`
                );
            }
            if (!this.elementIsEnabled) {
                errors.push(
                    `BUT: Element is not enabled. TIP: You can use :enable to wait the element is enabled before doing action on it.`
                );
            }
            if (!this.parentFrameIsReady) {
                errors.push(`BUT: parent frame is not ready ([is-ready='false']).`);
            }
        } else {
            const checkElement = hoot.queryFirst(this.trigger);
            if (checkElement) {
                errors.push(`Element has been found.`);
                errors.push(
                    `BUT: Element is not visible. TIP: You can use :not(:visible) to force the search for an invisible element.`
                );
            } else {
                errors.push(`Element (${this.trigger}) has not been found.`);
            }
        }
        return errors;
    }

    /**
     * When return null or false, macro continues.
     */
    async doAction(element) {
        if (this.skipped) {
            return false;
        }
        return await callWithUnloadCheck(async () => {
            const actionHelper = new TourHelpers(element);
            if (typeof this.run === "function") {
                await this.run.call({ anchor: element }, actionHelper);
            } else if (typeof this.run === "string") {
                for (const todo of this.run.split("&&")) {
                    const m = String(todo)
                        .trim()
                        .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                    await actionHelper[m.groups?.action](m.groups?.arguments);
                }
            }
        });
    }

    findTrigger(trigger) {
        if (!this.active) {
            this.skipped = true;
            return true;
        }
        return new TourStepTrigger(trigger, this.hasAction).find();
    }

    get hasAction() {
        return ["string", "function"].includes(typeof this.run) && !this.skipped;
    }
}
