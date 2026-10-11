import * as hoot from "@odoo/hoot-dom";
import { utils } from "@web/core/ui/ui_utils";
import { pick } from "@web/core/utils/objects";
import { session } from "@web/session";
import { TourTarget } from "@web_tour/tour_engine/tour_target";
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
     * An action of a tour: one command of the `run` of a step, performed by a
     * human or by the robot on its {@link TourTarget}.
     * @param {TourStep} step the step the action comes from
     * @param {string|null} event the command to perform, null when nothing has
     *      to be performed
     * @param {string} targetSelector the selector of the element the action waits
     *      for, points to and acts on
     * @param {string|undefined} listenedEvent the command whose events consume
     *      the action, when it isn't `event` or isn't performed on the target
     *      (only for the robot, e.g. the "drop" of `drag_and_drop`)
     * @param {string|undefined} listenedSelector the selector of the element
     *      whose events consume the action, along with `listenedEvent` (e.g.
     *      `.other` for `click .other`, the drop zone for `drag_and_drop`)
     * @param {"auto"|"manual"} mode the mode of the tour
     * @param {boolean} isRobot whether the robot performs the action
     * @param {boolean} debugMode whether the tour runs in debug mode
     * @param {number} stepDelay the delay the robot waits before performing the
     *      action, in ms
     */
    constructor(
        step,
        event,
        targetSelector,
        listenedEvent,
        listenedSelector,
        mode,
        isRobot,
        debugMode,
        stepDelay
    ) {
        const hasAction = ["string", "function"].includes(typeof step.run);
        this.step = step;
        this.event = event;
        this.target = new TourTarget(targetSelector, event, hasAction);
        this.listenedTarget = listenedSelector
            ? new TourTarget(listenedSelector, listenedEvent, false)
            : undefined;
        this.mode = mode;
        this.isRobot = isRobot;
        this.debugMode = debugMode;
        this.stepDelay = stepDelay;
    }

    /**
     * Content of the pointer when the step has none, depending on the event.
     * @returns {string}
     */
    get defaultContent() {
        switch (this.event) {
            case "click":
                return `Click on element`;
            case "edit":
                return `Edit element`;
            case "drag":
            case "drop":
                return `Drag element`;
            case "press":
                return `Press Enter`;
            case "hover":
                return `Hover element`;
            default:
                return ``;
        }
    }

    /**
     * Time allowed to find the trigger, in ms: unlimited for a human, or when
     * pausing in debug mode. Otherwise, the timeout of the step, or 10 seconds,
     * plus the step delay.
     * @returns {number}
     */
    get timeout() {
        if (!this.isRobot || (this.step.pause && this.debugMode)) {
            return Infinity;
        }
        return (this.step.timeout || 10000) + this.stepDelay;
    }

    /**
     * Check if a step is active dependant on step.isActive property
     * Note that when step.isActive is not defined, the step is active by default.
     * When a step is not active, it's just skipped and the tour continues to the next step.
     * @returns {boolean}
     */
    get active() {
        const mode = this.mode;
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
        const isActiveArray = Array.isArray(this.step.isActive) ? this.step.isActive : [];
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
        const checkRobot = !isActiveArray.includes("robot") || this.isRobot;
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
     * Executes this action's `run` on the given element.
     * When return null or false, macro continues.
     * @param {HTMLElement} element
     * @returns {Promise<any>}
     */
    async doAction(element) {
        const actionHelper = new TourHelpers(element);
        if (typeof this.step.run === "function") {
            return await this.step.run.call({ anchor: element }, actionHelper);
        } else if (typeof this.step.run === "string") {
            let lastResult = null;
            for (const todo of this.step.run.split("&&")) {
                const m = String(todo)
                    .trim()
                    .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                lastResult = await actionHelper[m.groups?.action](m.groups?.arguments);
            }
            return lastResult;
        }
    }

    /**
     * The step of the action as JSON, used to log it and to describe a failure.
     * @returns {string}
     */
    get stringify() {
        return (
            JSON.stringify(
                pick(
                    this.step,
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

    /**
     * Lists the events meaning that the action has been performed on the given
     * element, e.g. a click, an input or a drop on the expected zone, including
     * the equivalent keyboard interactions (Enter, Tab) and the selection of an
     * autocomplete item. They are the events of the command of the listened
     * target when the action has one, of its own command otherwise.
     * @param {HTMLElement} element
     * @returns {ConsumeEvent[]}
     */
    getConsumeEvents(element) {
        const consumedTarget = this.listenedTarget || this.target;
        const runCommand = consumedTarget.event;
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
                if (!isAutocompleteInput || this.isRobot) {
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
                const dropTarget = consumedTarget.find() || element;
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
