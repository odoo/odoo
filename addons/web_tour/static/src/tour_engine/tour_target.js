import * as hoot from "@odoo/hoot-dom";
import { getTag } from "@web/core/utils/xml";

export class TourTarget {
    /**
     * The element an action of a tour acts on, looked for through its selector:
     * the tour waits for it to be found and usable, points to it, and listens to
     * the events performing the action on it.
     * @param {string} selector the selector of the element
     * @param {string|null} event the command performed on the element, null when
     *      nothing has to be performed
     * @param {boolean} hasAction whether the step of the action has something to
     *      run, in which case the element must be enabled and not below a modal
     */
    constructor(selector, event, hasAction) {
        this.selector = selector;
        this.event = event;
        this.hasAction = hasAction;
        this.matchedEl = null;
    }

    /**
     * Looks for the target: the element matching the selector when it can be
     * acted on (see {@link queryMatchedEl}), or its draggable, contenteditable or
     * sortable container for the drag, input and sort events.
     * @returns {HTMLElement|undefined}
     */
    find() {
        const el = this.queryMatchedEl();
        if (!el) {
            return undefined;
        }

        if (this.event === "drag") {
            // jQuery-ui draggable triggers 'drag' events on the .ui-draggable element,
            // but the tip is attached to the .ui-draggable-handle element which may
            // be one of its children (or the element itself
            return (
                el.closest(
                    ".ui-draggable, .o_draggable, .o_we_draggable, .o-draggable, [draggable='true']"
                ) || el
            );
        }
        if (this.event === "input" && !["textarea", "input"].includes(el.tagName.toLowerCase())) {
            return el.closest("[contenteditable='true']");
        }
        if (this.event === "sort") {
            // when an element is dragged inside a sortable container (with classname
            // 'ui-sortable'), jQuery triggers the 'sort' event on the container
            return el.closest(".ui-sortable, .o_sortable");
        }
        return el;
    }

    /**
     * Looks for the element matching the selector, visible unless the selector
     * says otherwise, and keeps it as {@link matchedEl}. Returns it when it can be
     * acted on: the UI isn't blocked, the element is enabled and not below a
     * modal, and its frame and the website page are ready.
     * @returns {HTMLElement|false}
     */
    queryMatchedEl() {
        const visible = !/:(hidden|visible)\b/.test(this.selector);
        this.matchedEl = hoot.queryFirst(this.selector, { visible });
        if (this.matchedEl) {
            return !this.isUIBlocked &&
                this.matchedElIsEnabled &&
                this.matchedElIsInModal &&
                this.parentFrameIsReady &&
                this.frontendBodyIsReady
                ? this.matchedEl
                : false;
        }
        return false;
    }

    /**
     * On a website page, whether its interactions are bound to the elements
     * (`is-ready` body attribute).
     * @returns {boolean}
     */
    get frontendBodyIsReady() {
        if (document.documentElement.hasAttribute("data-website-id")) {
            return document.body.getAttribute("is-ready") === "true";
        } else {
            return true;
        }
    }

    /**
     * Whether the UI is blocked, e.g. while an RPC is pending.
     * @returns {boolean|Element|null}
     */
    get isUIBlocked() {
        return (
            document.body.classList.contains("o_ui_blocked") ||
            document.querySelector(".o_blockUI") ||
            document.querySelector(".o_is_blocked")
        );
    }

    /**
     * Whether the iframe containing the matched element, if any, is ready
     * (`is-ready` body attribute), unless the selector already checks `is-ready`
     * itself.
     * @returns {boolean}
     */
    get parentFrameIsReady() {
        if (this.selector.match(/\[is-ready=(true|false)\]/)) {
            return true;
        }
        const parentFrame = hoot.getParentFrame(this.matchedEl);
        return parentFrame && parentFrame.contentDocument.body.hasAttribute("is-ready")
            ? parentFrame.contentDocument.body.getAttribute("is-ready") === "true"
            : true;
    }

    /**
     * When a modal is in the overlay and that the current step has an action,
     * this method checks if the matched element is in the more front overlay.
     * @returns {boolean}
     */
    get matchedElIsInModal() {
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
        if (!modal || this.selector.startsWith("body")) {
            return true;
        }
        // Case 1: the trigger element is in modal
        if (isIn(this.matchedEl, modal)) {
            return true;
        }
        // Case 2: the trigger element is in notification
        const notificationContainer = hoot.queryFirst(".o_notification_manager");
        if (isIn(this.matchedEl, notificationContainer)) {
            return true;
        }
        // Case 3: the trigger element is in overlay
        const overlayContainer = hoot.queryFirst(".o-overlay-container");
        if (isIn(this.matchedEl, overlayContainer)) {
            // And the modal also, then we check if the parent overlay is in front the modal.
            if (isIn(modal, overlayContainer)) {
                const modalOverlay = modal.closest(".o-overlay-item");
                const overlays = Array.from(modalOverlay.parentElement.children).filter((el) =>
                    el.classList.contains("o-overlay-item")
                );
                const overlaysInFrontModal = overlays.slice(overlays.indexOf(modalOverlay) + 1);
                return overlaysInFrontModal.some((overlay) => isIn(this.matchedEl, overlay));
            }
            // For any other cases, it's not possible to check if the trigger element
            // is in front of behind the modal
            return true;
        }
        return false;
    }

    /**
     * Whether the matched element can be acted on: an input or a textarea must be
     * editable, a button or a select enabled. Always true for a step without any
     * action.
     * @returns {boolean}
     */
    get matchedElIsEnabled() {
        const isTag = (array) => array.includes(getTag(this.matchedEl, true));
        if (this.hasAction) {
            if (isTag(["input", "textarea"])) {
                return hoot.isEditable(this.matchedEl);
            } else if (isTag(["button", "select"])) {
                return !this.matchedEl.disabled;
            }
        }
        return true;
    }

    /**
     * Describes why {@link find} hasn't found the target yet, for diagnostics
     * when giving up on it (e.g. a timed-out wait).
     * @returns {string[]}
     */
    get error() {
        const errors = [];
        if (this.matchedEl) {
            errors.push(`Element has been found.`);
            if (this.isUIBlocked) {
                errors.push("BUT: DOM is blocked by UI.");
            }
            if (!this.matchedElIsInModal) {
                errors.push(
                    `BUT: It is not allowed to do action on an element that's below a modal.`
                );
            }
            if (!this.matchedElIsEnabled) {
                errors.push(
                    `BUT: Element is not enabled. TIP: You can use :enable to wait the element is enabled before doing action on it.`
                );
            }
            if (!this.parentFrameIsReady) {
                errors.push(`BUT: parent frame is not ready ([is-ready='false']).`);
            }
        } else {
            const checkElement = hoot.queryFirst(this.selector);
            if (checkElement) {
                errors.push(`Element has been found.`);
                errors.push(
                    `BUT: Element is not visible. TIP: You can use :not(:visible) to force the search for an invisible element.`
                );
            } else {
                errors.push(`Element (${this.selector}) has not been found.`);
            }
        }
        return errors;
    }
}
