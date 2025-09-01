import { tourState } from "@web_tour/js/tour_state";
import { debounce } from "@web/core/utils/timing";
import * as hoot from "@odoo/hoot-dom";
import { utils } from "@web/core/ui/ui_service";
import { TourStep } from "@web_tour/js/tour_step";
import { MacroMutationObserver } from "@web/core/macro";
import { getScrollParent } from "@web_tour/js/utils/tour_utils";

/**
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} conditional
 */

export class TourInteractive {
    mode = "manual";
    currentAction;
    currentActionIndex;
    anchorEls = [];
    removeListeners = () => {};

    /**
     * @param {Tour} data
     */
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map((step) => new TourStep(step, this));
        this.actions = this.steps.flatMap((s) => this.getSubActions(s));
        this.isBusy = false;
    }

    /**
     * @param {import("@web_tour/js/tour_pointer/tour_pointer").TourPointer} pointer
     * @param {Function} onTourEnd
     */
    start(env, pointer, onTourEnd) {
        env.bus.addEventListener("ACTION_MANAGER:UPDATE", () => (this.isBusy = true));
        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", () => (this.isBusy = false));

        this.pointer = pointer;
        this.debouncedToggleOpen = debounce(this.pointer.showContent, 50, true);
        this.onTourEnd = onTourEnd;
        this.observer = new MacroMutationObserver(() => this._onMutation());
        this.observer.observe(document.body);
        this.currentActionIndex = tourState.getCurrentIndex();
        this.play();
    }

    backward() {
        let tempIndex = this.currentActionIndex;
        let tempAction,
            tempAnchors = [];
        while (!tempAnchors.length && tempIndex >= 0) {
            tempIndex--;
            tempAction = this.actions.at(tempIndex);
            if (!tempAction.step.active) {
                continue;
            }
            tempAnchors = tempAction && this.findTriggers(tempAction.anchor);
        }

        if (tempIndex >= 0) {
            this.currentActionIndex = tempIndex;
            this.play();
        }
    }

    /**
     * @returns {HTMLElement[]}
     */
    findTriggers(anchor) {
        if (!anchor) {
            anchor = this.currentAction.anchor;
        }

        return anchor
            .split(/,\s*(?![^(]*\))/)
            .map((part) => hoot.queryFirst(part, { visible: true }))
            .filter((el) => !!el)
            .map((el) => this.getAnchorEl(el, this.currentAction.event))
            .filter((el) => !!el);
    }

    play() {
        this.removeListeners();
        if (this.currentActionIndex === this.actions.length) {
            this.observer.disconnect();
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
        this.anchorEls = this.findTriggers();
        this.setActionListeners();
        this.updatePointer();
    }

    updatePointer() {
        if (this.anchorEls.length) {
            this.pointer.pointTo(
                this.anchorEls[0],
                this.currentAction.pointerInfo,
                this.currentAction.event === "drop"
            );
            this.pointer.setState({
                onMouseEnter: () => this.debouncedToggleOpen(true),
                onMouseLeave: () => this.debouncedToggleOpen(false),
            });
        }
    }

    setActionListeners() {
        const cleanups = this.anchorEls.flatMap((anchorEl, index) => {
            const toListen = {
                anchorEl,
                consumeEvents: this.getConsumeEventType(anchorEl, this.currentAction.event),
                onConsume: () => {
                    this.pointer.hide();
                    this.currentActionIndex++;
                    this.play();
                },
                onError: () => {
                    if (this.currentAction.event === "drop") {
                        this.pointer.hide();
                        this.currentActionIndex--;
                        this.play();
                    }
                },
            };
            if (index === 0) {
                return this.setupListeners({
                    ...toListen,
                    onMouseEnter: () => this.pointer.showContent(true),
                    onMouseLeave: () => this.pointer.showContent(false),
                    onScroll: () => this.updatePointer(),
                });
            } else {
                return this.setupListeners({
                    ...toListen,
                    onScroll: () => {},
                });
            }
        });
        this.removeListeners = () => {
            this.anchorEls = [];
            while (cleanups.length) {
                cleanups.pop()();
            }
        };
    }

    /**
     * @param {HTMLElement} params.anchorEl
     * @param {import("../../tour_utils").ConsumeEvent[]} params.consumeEvents
     * @param {() => void} params.onMouseEnter
     * @param {() => void} params.onMouseLeave
     * @param {(ev: Event) => any} params.onScroll
     * @param {(ev: Event) => any} params.onConsume
     * @param {() => any} params.onError
     */
    setupListeners({
        anchorEl,
        consumeEvents,
        onMouseEnter,
        onMouseLeave,
        onScroll,
        onConsume,
        onError = () => {},
    }) {
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
        anchorEl.addEventListener("mouseenter", onMouseEnter);
        anchorEl.addEventListener("mouseleave", onMouseLeave);

        const cleanups = [
            () => {
                for (const consume of consumeEvents) {
                    consume.target.removeEventListener(consume.type, consume.listener, true);
                }
                anchorEl.removeEventListener("mouseenter", onMouseEnter);
                anchorEl.removeEventListener("mouseleave", onMouseLeave);
            },
        ];

        const scrollEl = getScrollParent(anchorEl);
        if (scrollEl) {
            const debouncedOnScroll = debounce(onScroll, 50);
            scrollEl.addEventListener("scroll", debouncedOnScroll);
            cleanups.push(() => scrollEl.removeEventListener("scroll", debouncedOnScroll));
        }

        return cleanups;
    }

    /**
     *
     * @param {import("../tour_service").TourStep} step
     * @returns {{
     *  event: string,
     *  anchor: string,
     *  pointerInfo: { tooltipPosition: string?, content: string? },
     * }[]}
     */
    getSubActions(step) {
        const actions = [];
        if (!step.run || typeof step.run === "function") {
            actions.push({
                step,
                event: "warn",
                anchor: step.trigger,
            });
            return actions;
        }

        for (const todo of step.run.split("&&")) {
            const m = String(todo)
                .trim()
                .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);

            let action = m.groups?.action;
            const anchor = m.groups?.arguments || step.trigger;
            const pointerInfo = {
                content: step.content,
                tooltipPosition: step.tooltipPosition,
            };

            if (action === "drag_and_drop") {
                actions.push({
                    step,
                    event: "drag",
                    anchor: step.trigger,
                    pointerInfo,
                });
                action = "drop";
            }

            actions.push({
                step,
                event: action,
                anchor: action === "edit" ? step.trigger : anchor,
                pointerInfo,
            });
        }

        return actions;
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
                                const nextStep = this.actions.at(this.currentActionIndex + 1);
                                if (
                                    this.findTriggers(nextStep.anchor)
                                        .at(0)
                                        ?.closest(".o-autocomplete--dropdown-item")
                                ) {
                                    // Skip the next step if the next one is a click on a dropdown item
                                    this.currentActionIndex++;
                                }
                                return true;
                            }
                        },
                    });
                    consumeEvents.push({
                        name: "click",
                        target: element.ownerDocument,
                        conditional: (ev) => {
                            if (ev.target.closest(".o-autocomplete--dropdown-item")) {
                                const nextStep = this.actions.at(this.currentActionIndex + 1);
                                if (
                                    this.findTriggers(nextStep.anchor)
                                        .at(0)
                                        ?.closest(".o-autocomplete--dropdown-item")
                                ) {
                                    // Skip the next step if the next one is a click on a dropdown item
                                    this.currentActionIndex++;
                                }
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

    /**
     * Returns the element that will be used in listening to the `consumeEvent`.
     * @param {HTMLElement} el
     * @param {string} consumeEvent
     */
    getAnchorEl(el, consumeEvent) {
        if (consumeEvent === "drag") {
            // jQuery-ui draggable triggers 'drag' events on the .ui-draggable element,
            // but the tip is attached to the .ui-draggable-handle element which may
            // be one of its children (or the element itself
            return el.closest(
                ".ui-draggable, .o_draggable, .o_we_draggable, .o-draggable, [draggable='true']"
            );
        }

        if (consumeEvent === "input" && !["textarea", "input"].includes(el.tagName.toLowerCase())) {
            return el.closest("[contenteditable='true']");
        }
        if (consumeEvent === "sort") {
            // when an element is dragged inside a sortable container (with classname
            // 'ui-sortable'), jQuery triggers the 'sort' event on the container
            return el.closest(".ui-sortable, .o_sortable");
        }
        return el;
    }

    _onMutation() {
        if (this.currentAction) {
            const tempAnchors = this.findTriggers();
            if (
                tempAnchors.length &&
                (tempAnchors.some((a) => !this.anchorEls.includes(a)) ||
                    this.anchorEls.some((a) => !tempAnchors.includes(a)))
            ) {
                this.removeListeners();
                this.anchorEls = tempAnchors;
                this.setActionListeners();
            } else if (!tempAnchors.length && this.anchorEls.length) {
                this.pointer.hide();
                if (
                    !hoot.queryFirst(".o_home_menu", { visible: true }) &&
                    !hoot.queryFirst(".dropdown-item.o_loading", { visible: true }) &&
                    !this.isBusy
                ) {
                    this.backward();
                }
                return;
            }
            this.updatePointer();
        }
    }
}
