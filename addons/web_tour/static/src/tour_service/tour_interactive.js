import { tourState } from "./tour_state";
import { debounce } from "@web/core/utils/timing";
import { getScrollParent, isActive } from "./tour_utils";
import * as hoot from "@odoo/hoot-dom";
import { utils } from "@web/core/ui/ui_service";

/**
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} conditional
 */

export class TourInteractive {
    constructor() {
        this.anchorEl;
        this.currentAction;
        this.currentActionIndex;
        this.removeListeners = () => {};
    }

    /**
     * @param {import("./tour_service").Tour} tour
     * @param {import("@web_tour/tour_pointer/tour_pointer").TourPointer} pointer
     * @param {Function} onTourEnd
     */
    loadTour(tour, pointer, onTourEnd) {
        this.tourName = tour.name;
        this.actions = tour.steps.flatMap((s) => this.getSubActions(s));
        this.pointer = pointer;
        this.debouncedToggleOpen = debounce(this.pointer.showContent, 50, true);
        this.onTourEnd = onTourEnd;
    }

    /**
     *
     * @param {Number} stepAt Step to start at
     */
    start(stepAt = 0) {
        this.pointer.start();
        this.observerDisconnect = hoot.observe(document.body, () => this._onMutation());
        this.currentActionIndex = stepAt;
        this.play();
    }

    backward() {
        let tempIndex = this.currentActionIndex;
        let tempAction, tempAnchor;

        while (!tempAnchor && tempIndex >= 0) {
            tempIndex--;
            tempAction = this.actions.at(tempIndex);
            if (!isActive({ isActive: tempAction.isActive }, "manual")) {
                continue;
            }
            tempAnchor = tempAction && hoot.queryFirst(tempAction.anchor);
        }

        if (tempIndex >= 0) {
            this.currentActionIndex = tempIndex;
            this.play();
        }
    }

    play() {
        this.removeListeners();
        if (this.currentActionIndex === this.actions.length) {
            this.observerDisconnect();
            this.onTourEnd();
            return;
        }

        this.currentAction = this.actions.at(this.currentActionIndex);

        if (this.currentAction.event === "warn") {
            console.warn(`Step '${this.currentAction.anchor}' ignored because no 'run'`);
            this.currentActionIndex++;
            this.play();
        }

        if (!isActive({ isActive: this.currentAction.isActive }, "manual")) {
            this.currentActionIndex++;
            this.play();
            return;
        }

        console.log(this.currentAction.event, this.currentAction.anchor);
        this.anchorEl = hoot.queryFirst(this.currentAction.anchor, { visible: true });

        tourState.set(this.tourName, "currentIndex", this.currentActionIndex);
        this.setActionListeners();
    }

    updatePointer() {
        this.pointer.pointTo(
            this.anchorEl,
            this.currentAction.pointerInfo,
            this.currentAction.event === "drop"
        );
        this.pointer.setState({
            onMouseEnter: () => this.debouncedToggleOpen(true),
            onMouseLeave: () => this.debouncedToggleOpen(false),
        });
    }

    setActionListeners() {
        if (this.anchorEl) {
            this.anchorEl = this.getAnchorEl(this.anchorEl, this.currentAction.event);
            const consumeEvents = this.getConsumeEventType(this.anchorEl, this.currentAction.event);
            this.removeListeners = this.setupListeners({
                anchorEl: this.anchorEl,
                consumeEvents,
                onMouseEnter: () => this.pointer.showContent(true),
                onMouseLeave: () => this.pointer.showContent(false),
                onScroll: () => this.updatePointer(),
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
            });
            this.updatePointer();
        }
    }

    /**
     * @param {HTMLElement} params.anchorEl
     * @param {import("./tour_utils").ConsumeEvent[]} params.consumeEvents
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

        return () => {
            while (cleanups.length) {
                cleanups.pop()();
            }
        };
    }

    /**
     *
     * @param {import("./tour_service").TourStep} step
     * @returns {{
     *  event: string,
     *  anchor: string,
     *  altAnchor: string?,
     *  isActive: string[]?,
     *  pointerInfo: { tooltipPosition: string?, content: string? },
     * }[]}
     */
    getSubActions(step) {
        const actions = [];
        if (!step.run || typeof step.run === "function") {
            actions.push({
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
                    event: "drag",
                    anchor: step.trigger,
                    pointerInfo,
                    isActive: step.isActive,
                });
                action = "drop";
            }

            actions.push({
                event: action,
                anchor: action === "edit" ? step.trigger : anchor,
                altAnchor: step.alt_trigger,
                pointerInfo,
                isActive: step.isActive,
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
                target: document,
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
            // be one of its children (or the element itself)
            return el.closest(".ui-draggable, .o_draggable, .o_we_draggable");
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
            let tempAnchor = hoot.queryFirst(this.currentAction.anchor, { visible: true });
            tempAnchor = tempAnchor && this.getAnchorEl(tempAnchor, this.currentAction.event);
            if (
                (!this.anchorEl && tempAnchor) ||
                (this.anchorEl && tempAnchor && tempAnchor !== this.anchorEl)
            ) {
                this.anchorEl = tempAnchor;
                this.removeListeners();
                this.setActionListeners();
            } else if (!tempAnchor && this.anchorEl) {
                this.pointer.hide();
                this.anchorEl = tempAnchor;
                if (!hoot.queryFirst(".o_home_menu", { visible: true })) {
                    this.backward();
                }
            }
            this.updatePointer();
        }
    }
}
