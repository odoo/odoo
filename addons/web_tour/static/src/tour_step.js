import { session } from "@web/session";
import { utils } from "@web/core/ui/ui_utils";
import * as hoot from "@odoo/hoot-dom";
import { pick } from "@web/core/utils/objects";
import { getTag } from "@web/core/utils/xml";
import { TourHelpers } from "@web_tour/tour_helpers/tour_helpers";

/**
 * @typedef TourStep
 * @property {"enterprise"|"community"|"mobile"|"desktop"|HootSelector[][]} isActive Active the step following {@link isActiveStep} filter
 * @property {string} [id]
 * @property {HootSelector} trigger The node on which the action will be executed.
 * @property {string} [content] Description of the step.
 * @property {"top" | "bottom" | "left" | "right"} [position] The position where the UI helper is shown.
 * @property {RunCommand} [run] The action to perform when trigger conditions are verified.
 * @property {number} [timeout] By default, when the trigger node isn't found after 10000 milliseconds, it throws an error.
 * You can change this value to lengthen or shorten the time before the error occurs [ms].
 */
export class TourStep {
    skipped = false;

    constructor(data, tour) {
        Object.assign(this, data);
        this.tour = tour;
    }

    /**
     * Check if a step is active dependant on step.isActive property
     * Note that when step.isActive is not defined, the step is active by default.
     * When a step is not active, it's just skipped and the tour continues to the next step.
     */
    get active() {
        this.checkHasTour();
        const mode = this.tour.mode;
        const isSmall = utils.isSmall();
        const standardKeyWords = ["enterprise", "community", "mobile", "desktop", "auto", "manual"];
        const isActiveArray = Array.isArray(this.isActive) ? this.isActive : [];
        if (isActiveArray.length === 0) {
            return true;
        }
        const selectors = isActiveArray.filter((key) => !standardKeyWords.includes(key));
        if (selectors.length) {
            // if one of selectors is not found, step is skipped
            for (const selector of selectors) {
                const el = hoot.queryFirst(selector);
                if (!el) {
                    return false;
                }
            }
        }
        const checkMode =
            isActiveArray.includes(mode) ||
            (!isActiveArray.includes("manual") && !isActiveArray.includes("auto"));
        const edition =
            (session.server_version_info || "").at(-1) === "e" ? "enterprise" : "community";
        const checkEdition =
            isActiveArray.includes(edition) ||
            (!isActiveArray.includes("enterprise") && !isActiveArray.includes("community"));
        const onlyForMobile = isActiveArray.includes("mobile") && isSmall;
        const onlyForDesktop = isActiveArray.includes("desktop") && !isSmall;
        const checkDevice =
            onlyForMobile ||
            onlyForDesktop ||
            (!isActiveArray.includes("mobile") && !isActiveArray.includes("desktop"));
        return checkEdition && checkDevice && checkMode;
    }

    checkHasTour() {
        if (!this.tour) {
            throw new Error(`TourStep instance must have a tour`);
        }
    }

    /**
     * @param {string} [selector] Defaults to this.trigger.
     * @returns {(HTMLElement|Boolean)}
     */
    findTrigger(selector = this.trigger) {
        if (!this.active) {
            this.skipped = true;
            return true;
        }
        this.activeSelector = selector;
        const visible = !/:(hidden|visible)\b/.test(selector);
        this.element = hoot.queryFirst(selector, { visible });
        if (this.element) {
            return !this.isUIBlocked &&
                this.elementIsEnabled &&
                this.elementIsInModal &&
                this.parentFrameIsReady &&
                this.frontendBodyIsReady
                ? this.element
                : false;
        }
        return false;
    }

    /** Wait interactions are bound to elements */
    get frontendBodyIsReady() {
        if (document.documentElement.hasAttribute("data-website-id")) {
            return document.body.getAttribute("is-ready") === "true";
        } else {
            return true;
        }
    }

    get isUIBlocked() {
        return (
            document.body.classList.contains("o_ui_blocked") ||
            document.querySelector(".o_blockUI") ||
            document.querySelector(".o_is_blocked")
        );
    }

    get parentFrameIsReady() {
        if (this.activeSelector.match(/\[is-ready=(true|false)\]/)) {
            return true;
        }
        const parentFrame = hoot.getParentFrame(this.element);
        return parentFrame && parentFrame.contentDocument.body.hasAttribute("is-ready")
            ? parentFrame.contentDocument.body.getAttribute("is-ready") === "true"
            : true;
    }

    /**
     * When a modal is in the overlay and that the current step has an action,
     * this method checks if the trigger element is in the more front overlay.
     */
    get elementIsInModal() {
        function isIn(element, parent) {
            if (!parent) {
                return false;
            }
            return parent.contains(hoot.getParentFrame(element)) || parent.contains(element);
        }

        if (!this.hasAction) {
            return true;
        }
        const modal = hoot.queryFirst(".modal:visible:not(.o_inactive_modal):last");
        if (!modal || this.activeSelector.startsWith("body")) {
            return true;
        }
        // Case 1: the trigger element is in modal
        if (isIn(this.element, modal)) {
            return true;
        }
        // Case 2: the trigger element is in notification
        const notificationContainer = hoot.queryFirst(".o_notification_manager");
        if (isIn(this.element, notificationContainer)) {
            return true;
        }
        // Case 3: the trigger element is in overlay
        const overlayContainer = hoot.queryFirst(".o-overlay-container");
        if (isIn(this.element, overlayContainer)) {
            // And the modal also, then we check if the parent overlay is in front the modal.
            if (isIn(modal, overlayContainer)) {
                const modalOverlay = modal.closest(".o-overlay-item");
                const overlays = Array.from(modalOverlay.parentElement.children).filter((el) =>
                    el.classList.contains("o-overlay-item")
                );
                const overlaysInFrontModal = overlays.slice(overlays.indexOf(modalOverlay) + 1);
                return overlaysInFrontModal.some((overlay) => isIn(this.element, overlay));
            }
            // For any other cases, it's not possible to check if the trigger element
            // is in front of behind the modal
            return true;
        }
        return false;
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

    get hasAction() {
        return ["string", "function"].includes(typeof this.run) && !this.skipped;
    }

    /**
     * Describes why {@link findTrigger} hasn't resolved this step's trigger yet,
     * for diagnostics when giving up on it (e.g. a timed-out wait).
     * @returns {string[]}
     */
    get error() {
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
            const checkElement = hoot.queryFirst(this.activeSelector);
            if (checkElement) {
                errors.push(`Element has been found.`);
                errors.push(
                    `BUT: Element is not visible. TIP: You can use :not(:visible) to force the search for an invisible element.`
                );
            } else {
                errors.push(`Element (${this.activeSelector}) has not been found.`);
            }
        }
        return errors;
    }

    /**
     * Executes this step's `run` on the given element.
     * When return null or false, macro continues.
     * @param {HTMLElement} element
     */
    async doAction(element) {
        if (this.skipped) {
            return false;
        }
        const actionHelper = new TourHelpers(element);
        if (typeof this.run === "function") {
            return await this.run.call({ anchor: element }, actionHelper);
        } else if (typeof this.run === "string") {
            let lastResult = null;
            for (const todo of this.run.split("&&")) {
                const m = String(todo)
                    .trim()
                    .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                lastResult = await actionHelper[m.groups?.action](m.groups?.arguments);
            }
            return lastResult;
        }
    }

    get describeMe() {
        this.checkHasTour();
        return (
            `[${this.index + 1}/${this.tour.steps.length}] Tour ${this.tour.name} → Step ` +
            (this.content ? `${this.content} (trigger: ${this.trigger})` : this.trigger)
        );
    }

    get stringify() {
        return (
            JSON.stringify(
                pick(
                    this,
                    "isActive",
                    "content",
                    "trigger",
                    "run",
                    "tooltipPosition",
                    "timeout",
                    "expectUnloadPage"
                ),
                (_key, value) => {
                    if (typeof value === "function") {
                        return "[function]";
                    } else {
                        return value;
                    }
                },
                2
            ) + ","
        );
    }
}
