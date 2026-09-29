import { utils } from "@web/core/ui/ui_utils";

/**
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} [conditional]
 * @property {boolean} [selectsDropdownItem]
 */

export class TourAction {
    /**
     * @param {Object} params
     * @param {import("./tour_step_interactive").TourStepInteractive} params.step
     * @param {string} params.event
     * @param {string} params.anchor
     */
    constructor({ step, event, anchor }) {
        this.step = step;
        this.event = event;
        this.anchor = anchor;
    }

    get content() {
        return this.step.content || this.defaultContent;
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

    get tooltipPosition() {
        return this.step.tooltipPosition;
    }

    /**
     * @returns {HTMLElement}
     */
    findTrigger() {
        const el = this.step.findTrigger(this.anchor);
        if (!el || el === true) {
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
                if (!isAutocompleteInput || this.step.tour.config.robot) {
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
            consumeEvents.push({
                name: "mouseenter",
                target: element,
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
