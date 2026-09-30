import * as hoot from "@odoo/hoot-dom";
import { utils } from "@web/core/ui/ui_utils";
import { pick } from "@web/core/utils/objects";
import { getTag } from "@web/core/utils/xml";
import { session } from "@web/session";
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

/**
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} [conditional]
 * @property {boolean} [selectsDropdownItem]
 */

export class TourAction {
    /**
     * @param {TourStep & { event: string|null, anchor: string, target?: string }} data
     * @param {import("./tour_engine").TourEngine} tour
     */
    constructor({ timeout, ...data }, tour) {
        Object.assign(this, data);
        this._timeout = timeout;
        this.tour = tour;
    }

    get defaultContent() {
        if (this.event === "click") {
            return `Click on element`;
        } else if (this.event === "edit") {
            return `Edit element`;
        } else if (["drag", "drop"].includes(this.event)) {
            return `Drag element`;
        } else if (this.event === "press") {
            return `Press ${this.anchor}`;
        } else if (this.event === "hover") {
            return `Hover element`;
        }
        return ``;
    }

    get debugMode() {
        return this.tour.debugMode;
    }

    get timeout() {
        if (!this.tour.isRobot || (this.pause && this.debugMode)) {
            return Infinity;
        }
        return this._timeout || this.tour.timeout || 10000;
    }

    /**
     * Check if a step is active dependant on step.isActive property
     * Note that when step.isActive is not defined, the step is active by default.
     * When a step is not active, it's just skipped and the tour continues to the next step.
     */
    get active() {
        const mode = this.tour.mode;
        const isSmall = utils.isSmall();
        const standardKeyWords = [
            "enterprise",
            "community",
            "mobile",
            "desktop",
            "auto",
            "manual",
            "robot",
        ];
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
        const checkRobot =
            !isActiveArray.includes("robot") || mode === "auto" || Boolean(this.tour.config?.robot);
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
        return checkEdition && checkDevice && checkMode && checkRobot;
    }

    /**
     * @returns {HTMLElement|false}
     */
    findAnchor() {
        const visible = !/:(hidden|visible)\b/.test(this.anchor);
        this.element = hoot.queryFirst(this.anchor, { visible });
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

    /**
     * @returns {HTMLElement}
     */
    findTrigger() {
        const el = this.findAnchor();
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
        if (this.anchor.match(/\[is-ready=(true|false)\]/)) {
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
        if (!modal || this.anchor.startsWith("body")) {
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
        return ["string", "function"].includes(typeof this.run);
    }

    /**
     * Describes why {@link findTrigger} hasn't resolved this action's trigger yet,
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
            const checkElement = hoot.queryFirst(this.anchor);
            if (checkElement) {
                errors.push(`Element has been found.`);
                errors.push(
                    `BUT: Element is not visible. TIP: You can use :not(:visible) to force the search for an invisible element.`
                );
            } else {
                errors.push(`Element (${this.anchor}) has not been found.`);
            }
        }
        return errors;
    }

    /**
     * Executes this action's `run` on the given element.
     * When return null or false, macro continues.
     * @param {HTMLElement} element
     */
    async doAction(element) {
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
        return (
            `[${this.index + 1}/${this.tour.actions.length}] Tour ${this.tour.name} → Step ` +
            (this.content ? `${this.content} (trigger: ${this.trigger})` : this.trigger)
        );
    }

    get stringify() {
        return (
            JSON.stringify(
                {
                    ...pick(this, "isActive", "content", "trigger", "run", "tooltipPosition"),
                    timeout: this._timeout,
                    ...pick(this, "expectUnloadPage"),
                },
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

    log() {
        if (this.debugMode) {
            console.groupEnd();
            console.groupCollapsed(this.describeMe);
            console.log(this.stringify);
            if (this.break) {
                // eslint-disable-next-line no-debugger
                debugger;
            }
        } else {
            console.log(this.describeMe);
        }
    }

    /**
     * @param {HTMLElement} anchorEl
     * @returns {HTMLElement|null}
     */
    findTarget(anchorEl) {
        if (!this.target) {
            return anchorEl;
        }
        return hoot.queryFirst(this.target, { visible: true }) || hoot.queryFirst(this.target);
    }

    /**
     * @param {HTMLElement} element
     * @returns {ConsumeEvent[]}
     */
    getConsumeEvents(element) {
        const runCommand = this.event;
        const consumeEvents = [];
        if (runCommand === "click") {
            consumeEvents.push({
                name: "click",
                target: element,
            });

            // Click on a field widget with an autocomplete should be also completed with a selection though Enter or Tab
            // This case is for the steps that click on field_widget
            if (element.querySelector(".o-autocomplete--input")) {
                consumeEvents.push({
                    name: "keydown",
                    target: element.querySelector(".o-autocomplete--input"),
                    conditional: (ev) =>
                        ["Tab", "Enter"].includes(ev.key) &&
                        ev.target.parentElement.querySelector(
                            ".o-autocomplete--dropdown-item .ui-state-active"
                        ),
                });
            }

            // Click on an element of a dropdown should be also completed with a selection though Enter or Tab
            // This case is for the steps that click on a dropdown-item
            if (element.closest(".o-autocomplete--dropdown-menu")) {
                consumeEvents.push({
                    name: "keydown",
                    target: element.closest(".o-autocomplete").querySelector("input"),
                    conditional: (ev) => ["Tab", "Enter"].includes(ev.key),
                });
            }

            // Press enter on a button do the same as a click
            if (element.tagName === "BUTTON") {
                consumeEvents.push({
                    name: "keydown",
                    target: element,
                    conditional: (ev) => ev.key === "Enter",
                });

                // Pressing enter in the input group does the same as clicking on the button
                if (element.closest(".input-group")) {
                    for (const inputEl of element.parentElement.querySelectorAll("input")) {
                        consumeEvents.push({
                            name: "keydown",
                            target: inputEl,
                            conditional: (ev) => ev.key === "Enter",
                        });
                    }
                }
            }
        }

        if (["fill", "edit"].includes(runCommand)) {
            if (
                utils.isSmall() &&
                element.closest(".o_field_widget")?.matches(".o_field_many2one, .o_field_many2many")
            ) {
                consumeEvents.push({
                    name: "click",
                    target: element,
                });
            } else {
                const isAutocompleteInput = element.classList.contains("o-autocomplete--input");
                if (!isAutocompleteInput || this.tour.isRobot) {
                    consumeEvents.push({
                        name: "input",
                        target: element,
                    });
                }
                if (isAutocompleteInput) {
                    consumeEvents.push({
                        name: "keydown",
                        target: element,
                        selectsDropdownItem: true,
                        conditional: (ev) =>
                            ["Tab", "Enter"].includes(ev.key) &&
                            ev.target.parentElement.querySelector(
                                ".o-autocomplete--dropdown-item .ui-state-active"
                            ),
                    });
                    consumeEvents.push({
                        name: "click",
                        target: element.ownerDocument,
                        selectsDropdownItem: true,
                        conditional: (ev) => ev.target.closest(".o-autocomplete--dropdown-item"),
                    });
                }
            }
        }

        if (runCommand === "hover") {
            const view = element.ownerDocument.defaultView;
            let target = element;
            while (target.parentElement && view.getComputedStyle(target).pointerEvents === "none") {
                target = target.parentElement;
            }
            consumeEvents.push({
                name: "pointerenter",
                target,
            });
        }

        // Drag & drop run command
        if (runCommand === "drag") {
            consumeEvents.push({
                name: "pointerdown",
                target: element,
            });
        }

        if (runCommand === "drop") {
            const conditional = (ev) => {
                const dropTarget = this.findTrigger() || element;
                const doc = dropTarget.ownerDocument;
                if (doc.elementsFromPoint(ev.clientX, ev.clientY).includes(dropTarget)) {
                    return true;
                }
                const rect = dropTarget.getBoundingClientRect();
                const x = Math.min(Math.max(ev.clientX, rect.left + 1), rect.right - 1);
                const y = Math.min(Math.max(ev.clientY, rect.top + 1), rect.bottom - 1);
                return doc.elementsFromPoint(x, y).includes(dropTarget);
            };
            consumeEvents.push({
                name: "pointerup",
                target: element.ownerDocument,
                conditional,
            });
            consumeEvents.push({
                name: "drop",
                target: element.ownerDocument,
                conditional,
            });
        }

        return consumeEvents;
    }
}
