import { tourState } from "@web_tour/js/tour_state";
import * as hoot from "@odoo/hoot-dom";
import { serializeChanges, serializeMutation } from "@web_tour/js/utils/tour_utils";
import { TourHelpers } from "@web_tour/js/tour_automatic/tour_helpers";
import { TourStep } from "@web_tour/js/tour_step";
import { getTag } from "@web/core/utils/xml";
import { MacroMutationObserver } from "@web/core/macro";

async function waitForMutations(target = document, timeout = 1000 / 16) {
    return new Promise((resolve) => {
        let observer;
        let timer;
        const mutationList = [];
        function onMutation(mutations) {
            mutationList.push(...(mutations || []));
            clearTimeout(timer);
            timer = setTimeout(() => {
                observer.disconnect();
                resolve(mutationList);
            }, timeout);
        }
        observer = new MacroMutationObserver(onMutation);
        observer.observe(target);
        onMutation([]);
    });
}
export class TourStepAutomatic extends TourStep {
    skipped = false;
    error = "";
    constructor(data, tour, index) {
        super(data, tour);
        this.index = index;
        this.tourConfig = tourState.getCurrentConfig();
    }

    async checkForUndeterminisms(initialElement, delay) {
        if (delay <= 0 || !initialElement) {
            return;
        }
        const tagName = initialElement.tagName?.toLowerCase();
        if (["body", "html"].includes(tagName) || !tagName) {
            return;
        }
        const snapshot = initialElement.cloneNode(true);
        const mutations = await waitForMutations(initialElement, delay);
        let reason;
        if (!hoot.isVisible(initialElement)) {
            reason = `Initial element is no longer visible`;
        } else if (!initialElement.isEqualNode(snapshot)) {
            reason =
                `Initial element has changed:\n` +
                JSON.stringify(serializeChanges(snapshot, initialElement), null, 2);
        } else if (mutations.length) {
            const changes = [...new Set(mutations.map(serializeMutation))];
            reason =
                `Initial element has mutated ${mutations.length} times:\n` +
                JSON.stringify(changes, null, 2);
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
    async doAction() {
        if (this.skipped) {
            return false;
        }
        const actionHelper = new TourHelpers(this.element);
        if (typeof this.run === "function") {
            return await this.run.call({ anchor: this.element }, actionHelper);
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
        if (!modal || this.trigger.startsWith("body")) {
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
}
