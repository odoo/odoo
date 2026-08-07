import { tourState } from "@web_tour/js/tour_state";
import * as hoot from "@odoo/hoot-dom";
import { utils } from "@web/core/ui/ui_service";
import { TourStepInteractive } from "@web_tour/js/tour_interactive/tour_step_interactive";
import { TourInteractiveObserver } from "@web_tour/js/tour_interactive/tour_interactive_observer";
import { pointerState } from "@web_tour/js/tour_pointer/tour_pointer";

/**
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} conditional
 */

export class TourInteractive {
    static observer = null;
    mode = "manual";
    currentAction;
    currentActionIndex;
    anchorEl;
    removeListeners = () => {};

    /**
     * @param {Tour} data
     */
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map((step) => new TourStepInteractive(step, this));
        this.actions = this.steps.flatMap((step) => step.actions);
        this.isBusy = false;
    }

    /**
     * @param {import("@web_tour/js/tour_pointer/tour_pointer").TourPointer} pointer
     * @param {Function} onTourEnd
     */
    start(env, onTourEnd) {
        this.onTourEnd = onTourEnd;
        if (TourInteractive.observer) {
            TourInteractive.observer.disconnect();
        }
        TourInteractive.observer = new TourInteractiveObserver(() => this._onMutation());
        TourInteractive.observer.observe(document.body);
        this.currentActionIndex = tourState.getCurrentIndex();
        this.play();
        env.bus.addEventListener("ACTION_MANAGER:UPDATE", () => (this.isBusy = true));
        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", () => (this.isBusy = false));
    }

    backward() {
        let tempIndex = this.currentActionIndex;
        let tempAction, tempAnchor;
        while (!tempAnchor && tempIndex >= 0) {
            tempIndex--;
            tempAction = this.actions.at(tempIndex);
            if (!tempAction.step.active || tempAction.event === "warn") {
                continue;
            }
            tempAnchor = tempAction.findTrigger();
        }

        if (tempIndex >= 0) {
            this.currentActionIndex = tempIndex;
            this.play();
        }
    }

    play() {
        this.removeListeners();
        if (this.currentActionIndex === this.actions.length) {
            TourInteractive.observer.disconnect();
            this.onTourEnd();
            return;
        }

        this.currentAction = this.actions.at(this.currentActionIndex);

        if (!this.currentAction.step.active || this.currentAction.event === "warn") {
            if (this.currentAction.event === "warn") {
                console.warn(`Step '${this.currentAction.anchor}' ignored.`);
            }
            this.currentActionIndex++;
            this.play();
            return;
        }

        console.log(this.currentAction.event, this.currentAction.anchor);

        tourState.setCurrentIndex(this.currentActionIndex);
        this.anchorEl = this.currentAction.findTrigger();
        this.setActionListeners();
        this.updatePointer();
    }

    updatePointer() {
        if (this.anchorEl) {
            pointerState.trigger = this.anchorEl;
            pointerState.content = this.currentAction.content;
            pointerState.position = this.currentAction.tooltipPosition;
            pointerState.isZone = this.currentAction.event === "drop";
        } else {
            pointerState.trigger = undefined;
        }
    }

    setActionListeners() {
        if (!this.anchorEl) {
            this.removeListeners = () => {};
            return;
        }
        const cleanups = this.setupListeners({
            consumeEvents: this.getConsumeEventType(this.anchorEl, this.currentAction.event),
            onConsume: () => {
                this.currentActionIndex++;
                this.play();
            },
            onError: () => {
                if (this.currentAction.event === "drop") {
                    this.currentActionIndex--;
                    this.play();
                }
            },
        });
        this.removeListeners = () => {
            this.anchorEl = undefined;
            while (cleanups.length) {
                cleanups.pop()();
            }
        };
    }

    /**
     * @param {import("../../tour_utils").ConsumeEvent[]} params.consumeEvents
     * @param {(ev: Event) => any} params.onConsume
     * @param {() => any} params.onError
     */
    setupListeners({ consumeEvents, onConsume, onError = () => {} }) {
        consumeEvents = consumeEvents.map((c) => ({
            target: c.target,
            type: c.name,
            listener: function (ev) {
                if (!c.conditional || c.conditional(ev)) {
                    onConsume();
                } else {
                    onError();
                }
            },
        }));

        for (const consume of consumeEvents) {
            consume.target.addEventListener(consume.type, consume.listener, true);
        }
        const cleanups = [
            () => {
                for (const consume of consumeEvents) {
                    consume.target.removeEventListener(consume.type, consume.listener, true);
                }
            },
        ];
        return cleanups;
    }

    /**
     * When the next action is a click on an autocomplete dropdown item, the
     * current "edit" action already consumed the selection (Tab/Enter or a
     * direct click on the item), so that next step would never see its own
     * trigger event fire.
     */
    skipNextActionIfDropdownItem() {
        const nextAction = this.actions.at(this.currentActionIndex + 1);
        if (nextAction.findTrigger()?.closest(".o-autocomplete--dropdown-item")) {
            this.currentActionIndex++;
        }
    }

    /**
     * @param {HTMLElement} [element]
     * @param {string} [runCommand]
     * @returns {ConsumeEvent[]}
     */
    getConsumeEventType(element, runCommand) {
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
                consumeEvents.push({
                    name: "input",
                    target: element,
                });
                if (element.classList.contains("o-autocomplete--input")) {
                    consumeEvents.push({
                        name: "keydown",
                        target: element,
                        conditional: (ev) => {
                            if (
                                ["Tab", "Enter"].includes(ev.key) &&
                                ev.target.parentElement.querySelector(
                                    ".o-autocomplete--dropdown-item .ui-state-active"
                                )
                            ) {
                                this.skipNextActionIfDropdownItem();
                                return true;
                            }
                        },
                    });
                    consumeEvents.push({
                        name: "click",
                        target: element.ownerDocument,
                        conditional: (ev) => {
                            if (ev.target.closest(".o-autocomplete--dropdown-item")) {
                                this.skipNextActionIfDropdownItem();
                                return true;
                            }
                        },
                    });
                }
            }
        }

        // Drag & drop run command
        if (runCommand === "drag") {
            consumeEvents.push({
                name: "pointerdown",
                target: element,
            });
        }

        if (runCommand === "drop") {
            consumeEvents.push({
                name: "pointerup",
                target: element.ownerDocument,
                conditional: (ev) =>
                    element.ownerDocument
                        .elementsFromPoint(ev.clientX, ev.clientY)
                        .includes(element),
            });
            consumeEvents.push({
                name: "drop",
                target: element.ownerDocument,
                conditional: (ev) =>
                    element.ownerDocument
                        .elementsFromPoint(ev.clientX, ev.clientY)
                        .includes(element),
            });
        }

        return consumeEvents;
    }

    _onMutation() {
        if (this.currentAction) {
            const tempAnchor = this.currentAction.findTrigger();
            if (tempAnchor && tempAnchor !== this.anchorEl) {
                this.removeListeners();
                this.anchorEl = tempAnchor;
                this.setActionListeners();
            } else if (!tempAnchor && this.anchorEl) {
                if (
                    !hoot.queryFirst(".o_home_menu", { visible: true }) &&
                    !hoot.queryFirst(".dropdown-item.o_loading", { visible: true }) &&
                    !this.isBusy
                ) {
                    this.backward();
                } else {
                    pointerState.trigger = undefined;
                }
                return;
            }
            this.updatePointer();
        }
    }
}
