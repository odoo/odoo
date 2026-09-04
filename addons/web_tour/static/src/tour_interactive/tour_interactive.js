import { markup } from "@odoo/owl";
import { tourState } from "@web_tour/tour_state";
import * as hoot from "@odoo/hoot-dom";
import { utils } from "@web/core/ui/ui_utils";
import { TourStepInteractive } from "@web_tour/tour_interactive/tour_step_interactive";
import { TourInteractiveObserver } from "@web_tour/tour_interactive/tour_interactive_observer";
import { TourPointer, pointerState } from "@web_tour/tour_pointer/tour_pointer";

/**
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} conditional
 */

export class TourInteractive {
    static observer = null;
    static removePointer = () => {};
    mode = "manual";
    currentAction;
    currentActionIndex;
    anchorEl;
    removeListeners = () => {};

    /**
     * @param {Tour} data
     * @param {Object} deps
     * @param {import("@web/core/network/orm_service").ORM} deps.orm
     * @param {import("@web/core/effects/effect_plugin").EffectPlugin} deps.effect
     * @param {import("@web/core/overlay/overlay_plugin").OverlayPlugin} deps.overlay
     * @param {(nextTour: Object) => void} deps.onChainNextTour
     */
    constructor(data, { orm, effect, overlay, onChainNextTour }) {
        this.orm = orm;
        this.effect = effect;
        this.overlay = overlay;
        this.onChainNextTour = onChainNextTour;
        Object.assign(this, data);
        this.steps = this.steps.map((step) => new TourStepInteractive(step, this));
        this.actions = this.steps.flatMap((step) => step.actions);
        this.isBusy = false;
        this.config = tourState.getCurrentConfig() || {};
        this.robotStep = null;
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     */
    start(env) {
        TourInteractive.removePointer();
        if (TourInteractive.observer) {
            TourInteractive.observer.disconnect();
        }
        TourInteractive.observer = new TourInteractiveObserver(() => this._onMutation());
        TourInteractive.observer.observe(document.body);
        TourInteractive.removePointer = this.overlay.add(
            TourPointer,
            { pointerState },
            { sequence: 1100 } // sequence based on bootstrap z-index values.
        );
        this.currentActionIndex = tourState.getCurrentIndex();
        if (this.config.debug && this.currentActionIndex === 0) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
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
            this.finish();
            return;
        }

        this.currentAction = this.actions.at(this.currentActionIndex);

        if (this.config.robot) {
            clearTimeout(this.robotWatchdog);
            const actionAtCall = this.currentAction;
            this.robotWatchdog = setTimeout(() => {
                if (this.currentAction === actionAtCall) {
                    throw new Error(
                        `Robot: no progress for 10s on step '${actionAtCall.anchor}'.\n` +
                            actionAtCall.step.error.join("\n")
                    );
                }
            }, 10000);
        }

        if (!this.currentAction.step.active) {
            this.currentActionIndex++;
            this.play();
            return;
        }

        if (this.currentAction.event === "warn") {
            if (!this.currentAction.findTrigger()) {
                return;
            }
            console.log(`Step '${this.currentAction.anchor}' ignored.`);
            this.currentActionIndex++;
            this.play();
            return;
        }

        console.log(this.currentAction.event, this.currentAction.anchor);

        tourState.setCurrentIndex(this.currentActionIndex);
        this.anchorEl = this.currentAction.findTrigger();
        this.setActionListeners();
        if (!this.config.robot && this.anchorEl && !this.hasConsumeEvent) {
            this.currentActionIndex++;
            this.play();
            return;
        }
        this.updatePointer();
    }

    async finish() {
        TourInteractive.removePointer();
        tourState.clear();
        let message = this.config.rainbowManMessage || this.rainbowManMessage;
        if (message && window.DOMPurify) {
            message = window.DOMPurify.sanitize(message);
            this.effect.add({
                type: "rainbow_man",
                message: markup(message),
            });
            if (this.config.robot) {
                await hoot.waitFor(".o_reward_rainbow_man", { timeout: 10000 });
            }
        }
        console.log("tour succeeded");

        const nextTour = await this.orm.call("web_tour.tour", "consume", [this.name]);
        if (nextTour) {
            this.onChainNextTour(nextTour);
        }
    }

    get hasConsumeEvent() {
        return this.getConsumeEventType(this.anchorEl, this.currentAction.event).length > 0;
    }

    updatePointer() {
        if (this.anchorEl) {
            pointerState.trigger = this.anchorEl;
            pointerState.content = this.currentAction.content;
            pointerState.position = this.currentAction.tooltipPosition;
            pointerState.isZone = this.currentAction.event === "drop";
            if (this.config.robot) {
                this.playRobot();
            }
        } else {
            pointerState.trigger = undefined;
        }
    }

    /**
     * Schedules the current step's {@link TourStepInteractive.doAction} once per
     * step, queued on {@link robotQueue} so steps never race each other: a step
     * like "edit" on an autocomplete input is considered consumed by the
     * interactive engine as soon as the first keystroke fires an "input" event,
     * well before the typing is done. That already advances the tour to the next
     * step (e.g. "click" on a dropdown item) and would call this again while the
     * previous step's typing is still in progress — exactly as a human could
     * never type and click the very same input at once.
     */
    playRobot() {
        const action = this.currentAction;
        const step = action.step;
        if (step === this.robotStep) {
            return;
        }
        this.robotStep = step;
        const selfAdvance = !this.hasConsumeEvent;
        this.robotQueue = (this.robotQueue || Promise.resolve()).then(async () => {
            await step.doAction();
            if (selfAdvance && this.currentAction === action) {
                this.currentActionIndex++;
                this.play();
            }
        });
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
                tourState.setCurrentIndex(this.currentActionIndex);
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
                const dropTarget = this.currentAction.findTrigger() || element;
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

    _onMutation() {
        if (this.currentAction?.event === "warn") {
            this.play();
            return;
        }
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
