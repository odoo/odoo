import { _legacyIsVisible } from "@web/core/utils/ui";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { callWithUnloadCheck } from "./tour_utils";
import { TourHelpers } from "./tour_helpers";
import { TourStep } from "./tour_step";
import { getTag } from "@web/core/utils/xml";

export class TourStepAutomatic extends TourStep {
    skipped = false;
    error = "";
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
            if (this.error) {
                errors.push(this.error);
            } else {
                errors.push(
                    `The cause is that trigger (${this.trigger}) element cannot be found in DOM. TIP: You can use :not(:visible) to force the search for an invisible element.`
                );
            }
        }
        return errors;
    }

    /**
     * When return true, macroEngine stops.
     * @returns {Boolean}
     */
    async doAction() {
        let result = false;
        if (!this.skipped) {
            // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
            const actionHelper = new TourHelpers(this.element);

            if (typeof this.run === "function") {
                const willUnload = await callWithUnloadCheck(async () => {
                    await this.run.call({ anchor: this.element }, actionHelper);
                });
                result = willUnload && "will unload";
            } else if (typeof this.run === "string") {
                for (const todo of this.run.split("&&")) {
                    const m = String(todo)
                        .trim()
                        .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                    await actionHelper[m.groups?.action](m.groups?.arguments);
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
            this.error = `HOOT: ${error.message}`;
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
}
