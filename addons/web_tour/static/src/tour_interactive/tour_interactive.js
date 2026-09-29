import { markup } from "@odoo/owl";
import { tourState } from "@web_tour/tour_state";
import * as hoot from "@odoo/hoot-dom";
import { Macro } from "@web/core/macro";
import { TourInteractiveObserver } from "@web_tour/tour_interactive/tour_interactive_observer";
import { TourStepInteractive } from "@web_tour/tour_interactive/tour_step_interactive";
import { TourPointer, pointerState } from "@web_tour/tour_pointer/tour_pointer";

export class TourInteractive {
    static current = null;
    static removePointer = () => {};
    static MAX_BACKWARD_ACTIONS = 10;
    mode = "manual";
    currentAction;
    currentActionIndex;
    anchorEl;
    consumeEvents = [];
    removeListeners = () => {};
    canSearch = true;
    searchedActionIndex = null;

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
        TourInteractive.current?.stop();
        TourInteractive.current = this;
        this.macro = new Macro({
            name: this.name,
            timeout: this.config.robot ? 10000 : Infinity,
            steps: this.actions.map((action, index) => ({
                trigger: () => this.shouldSearch(index) && this.track(action, index),
            })),
            onComplete: () => this.finish(),
            onError: ({ error, index }) => this.fail(error, this.actions[index]),
        });
        this.observer = new TourInteractiveObserver(() => (this.canSearch = true));
        this.observer.start(document);
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
        this.busController = new AbortController();
        const { signal } = this.busController;
        env.bus.addEventListener("ACTION_MANAGER:UPDATE", () => (this.isBusy = true), { signal });
        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", () => (this.isBusy = false), {
            signal,
        });
    }

    /**
     * Moves the tour back to the closest previous action whose trigger is in the
     * DOM, looking at most {@link TourInteractive.MAX_BACKWARD_ACTIONS} actions
     * back.
     */
    backward() {
        const fromIndex = Math.max(
            this.currentActionIndex - TourInteractive.MAX_BACKWARD_ACTIONS,
            0
        );
        for (let index = this.currentActionIndex - 1; index >= fromIndex; index--) {
            const action = this.actions[index];
            if (action.step.active && action.event !== "warn" && action.findTrigger()) {
                this.currentActionIndex = index;
                this.play();
                return;
            }
        }
    }

    play() {
        this.removeListeners();
        pointerState.trigger = undefined;
        this.canSearch = true;
        this.macro.play(this.currentActionIndex);
    }

    stop() {
        this.macro.stop();
        this.removeListeners();
        this.detach();
    }

    detach() {
        this.busController?.abort();
        this.observer?.disconnect();
        if (TourInteractive.current === this) {
            TourInteractive.current = null;
        }
    }

    /**
     * Called on every animation frame by the macro: the trigger of a newly
     * played action is looked for right away, then only once
     * {@link TourInteractiveObserver} flagged that the DOM may have changed.
     * @param {number} index
     * @returns {boolean}
     */
    shouldSearch(index) {
        if (!this.canSearch && index === this.searchedActionIndex) {
            return false;
        }
        this.canSearch = false;
        this.searchedActionIndex = index;
        return true;
    }

    track(action, index) {
        if (!action.step.active) {
            return true;
        }
        const anchor = action.findTrigger();
        if (action.event === "warn") {
            if (anchor) {
                console.log(`Step '${action.anchor}' ignored.`);
            }
            return anchor;
        }
        if (this.currentAction !== action) {
            this.removeListeners();
            this.currentAction = action;
            this.currentActionIndex = index;
            console.log(action.event, action.anchor);
            tourState.setCurrentIndex(index);
        }
        if (anchor) {
            if (anchor !== this.anchorEl) {
                this.removeListeners();
                this.anchorEl = anchor;
                this.setActionListeners();
                if (!this.config.robot && !this.consumeEvents.length) {
                    return true;
                }
            }
            this.updatePointer();
        } else if (this.anchorEl && !this.config.robot) {
            if (
                this.isBusy ||
                hoot.queryFirst(".o_home_menu", { visible: true }) ||
                hoot.queryFirst(".dropdown-item.o_loading", { visible: true })
            ) {
                pointerState.trigger = undefined;
            } else {
                this.backward();
            }
        }
        return false;
    }

    fail(error, action) {
        this.removeListeners();
        this.detach();
        TourInteractive.removePointer();
        pointerState.trigger = undefined;
        if (error.type === "Timeout") {
            console.error(
                `Robot: no progress for ${this.macro.timeout}ms on step '${action.anchor}'.\n` +
                    action.step.error.join("\n")
            );
        } else {
            console.error(error.message);
        }
    }

    async finish() {
        this.detach();
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
        const selfAdvance = !this.consumeEvents.length;
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
            this.consumeEvents = [];
            this.removeListeners = () => {};
            return;
        }
        this.consumeEvents = this.currentAction.getConsumeEvents(this.anchorEl);
        const cleanups = this.setupListeners({
            consumeEvents: this.consumeEvents,
            onConsume: ({ selectsDropdownItem }) => {
                if (selectsDropdownItem) {
                    this.skipNextActionIfDropdownItem();
                }
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
     * @param {import("./tour_action").ConsumeEvent[]} params.consumeEvents
     * @param {(consumeEvent: import("./tour_action").ConsumeEvent) => any} params.onConsume
     * @param {() => any} params.onError
     */
    setupListeners({ consumeEvents, onConsume, onError = () => {} }) {
        consumeEvents = consumeEvents.map((c) => ({
            target: c.target,
            type: c.name,
            listener: function (ev) {
                if (!c.conditional || c.conditional(ev)) {
                    onConsume(c);
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
        if (nextAction?.findTrigger()?.closest(".o-autocomplete--dropdown-item")) {
            this.currentActionIndex++;
        }
    }
}
