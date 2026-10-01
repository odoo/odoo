import * as hoot from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";
import { enableEventLogs, setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { Macro } from "@web/core/macro";
import { config as transitionConfig } from "@web/core/transition";
import { TourAction } from "@web_tour/tour_engine/tour_action";
import { TourPointer, pointerState } from "@web_tour/tour_pointer/tour_pointer";
import { tourState } from "@web_tour/tour_state";

const SELECTOR_COMMANDS = ["check", "clear", "click", "dblclick", "hover", "uncheck"];

export class TourEngine extends Macro {
    static current = null;
    static removePointer = () => {};
    allowUnload = true;
    currentAction;
    currentActionIndex;
    anchorEl;
    consumeEvents = [];
    isLost = false;
    removeListeners = () => {};

    /**
     * @param {Tour} data
     * @param {Object} deps
     * @param {import("@web/core/network/orm_service").ORM} deps.orm
     * @param {import("@web/core/effects/effect_plugin").EffectPlugin} deps.effect
     * @param {import("@web/core/overlay/overlay_plugin").OverlayPlugin} deps.overlay
     * @param {(nextTour: Object) => void} deps.onChainNextTour
     */
    constructor({ steps, ...data }, { orm, effect, overlay, onChainNextTour }) {
        super({ name: data.name, steps: [] });
        this.orm = orm;
        this.effect = effect;
        this.overlay = overlay;
        this.onChainNextTour = onChainNextTour;
        Object.assign(this, data);
        this.config = tourState.getCurrentConfig() || {};
        this.mode = this.config.mode === "auto" ? "auto" : "manual";
        this.isRobot = this.mode === "auto" || Boolean(this.config.robot);
        this.showPointer = this.config.pointer ?? this.mode === "manual";
        this.actions = steps.flatMap((step) => this.buildActions(step));
        this.actions.forEach((action, index) => (action.index = index));
        this.steps = this.actions.map((action) => ({
            trigger: () => this.track(action),
            timeout: action.timeout,
            ...(this.isRobot && action.event
                ? { action: (anchor) => this.perform(action, anchor) }
                : {}),
        }));
        this.isBusy = false;
    }

    get debugMode() {
        return this.config.debug !== false;
    }

    get describeWhereIFailed() {
        const offset = 3;
        const currentIndex = this.currentActionIndex;
        const start = Math.max(currentIndex - offset, 0);
        const end = Math.min(currentIndex + offset, this.actions.length - 1);
        const result = [];
        for (let i = start; i <= end; i++) {
            const action = this.actions[i];
            const text = [action.stringify];
            if (i === currentIndex) {
                const line = "-".repeat(10);
                const failing_step = `${line} FAILED: ${action.describeMe} ${line}`;
                text.unshift(failing_step);
                text.push("-".repeat(failing_step.length));
            }
            result.push(...text);
        }
        return result.join("\n");
    }

    backward() {
        let tempIndex = this.currentActionIndex;
        let tempAction, tempAnchor;
        while (!tempAnchor && tempIndex > 0) {
            tempIndex--;
            tempAction = this.actions.at(tempIndex);
            if (!tempAction.active || !tempAction.event) {
                continue;
            }
            tempAnchor = tempAction.findTrigger();
        }

        if (tempAnchor) {
            this.currentActionIndex = tempIndex;
            this.play();
        } else {
            this.isLost = true;
        }
    }

    /**
     * @param {import("./tour_action").TourStep} step
     * @returns {TourAction[]}
     */
    buildActions(step) {
        const addAction = (event, anchor, target) =>
            new TourAction({ ...step, event, anchor, target }, this);

        if (typeof step.run !== "string") {
            return [addAction(this.isRobot && step.run ? "run" : null, step.trigger)];
        }

        const commands = [];
        for (const todo of step.run.split("&&")) {
            const m = String(todo)
                .trim()
                .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
            const command = m.groups?.action;
            const argument = m.groups?.arguments;
            if (command === "drag_and_drop") {
                commands.push({ event: "drag", anchor: step.trigger });
                commands.push({ event: "drop", anchor: argument || step.trigger });
            } else {
                const anchor = (SELECTOR_COMMANDS.includes(command) && argument) || step.trigger;
                commands.push({ event: command, anchor });
            }
        }

        if (this.isRobot) {
            const [{ event, anchor }] = commands;
            return [addAction(event, step.trigger, anchor !== step.trigger ? anchor : undefined)];
        }
        return commands.map(({ event, anchor }) => addAction(event, anchor));
    }

    detach() {
        this.busController?.abort();
        if (TourEngine.current === this) {
            TourEngine.current = null;
        }
    }

    end() {
        this.detach();
        TourEngine.removePointer();
        pointerState.trigger = undefined;
        tourState.clear();
        if (!this.isRobot) {
            return;
        }
        delete window[this.hootNameSpace];
        transitionConfig.disabled = false;
        //No need to catch error yet.
        window.addEventListener(
            "error",
            (ev) => {
                ev.preventDefault();
                ev.stopImmediatePropagation();
            },
            true
        );
        window.addEventListener(
            "unhandledrejection",
            (ev) => {
                ev.preventDefault();
                ev.stopImmediatePropagation();
            },
            true
        );
    }

    /**
     * @param {TourAction} action
     */
    enter(action) {
        this.removeListeners();
        this.currentAction = action;
        this.currentActionIndex = action.index;
        tourState.setCurrentIndex(action.index);
        action.log();
    }

    next() {
        if (this.isRobot) {
            this.removeListeners();
            this.consumed.resolve();
        } else {
            this.play();
        }
    }

    async onComplete() {
        if (this.debugMode) {
            console.groupEnd();
        }
        this.end();
        let message = this.config.rainbowManMessage || this.rainbowManMessage;
        if (message && window.DOMPurify) {
            message = window.DOMPurify.sanitize(message);
            this.effect.add({
                type: "rainbow_man",
                message: markup(message),
            });
            if (this.isRobot) {
                await hoot.waitFor(".o_reward_rainbow_man", { timeout: 10000 });
            }
        }
        console.log("tour succeeded");
        // Used to see easily in the python console and to know which tour has been succeeded in suite tours case.
        const succeeded = `║ TOUR ${this.name} SUCCEEDED ║`;
        const msg = [succeeded];
        msg.unshift("╔" + "═".repeat(succeeded.length - 2) + "╗");
        msg.push("╚" + "═".repeat(succeeded.length - 2) + "╝");
        console.log(`\n\n${msg.join("\n")}\n`);

        if (this.mode === "manual") {
            const nextTour = await this.orm.call("web_tour.tour", "consume", [this.name]);
            if (nextTour) {
                this.onChainNextTour(nextTour);
            }
        }
    }

    onError({ error }) {
        this.removeListeners();
        if (error.type === "Timeout") {
            const errors = [...this.actions[this.currentActionIndex].error];
            if (this.awaitingConsume) {
                const names = this.consumeEvents.map((c) => c.name).join(", ");
                errors.push(`BUT: the action has been performed without triggering (${names}).`);
            }
            this.throwError(...errors, error.message);
        } else {
            this.throwError(error.message);
        }
        this.end();
    }

    async pause() {
        const styles = [
            "background: black; color: white; font-size: 14px",
            "background: black; color: orange; font-size: 14px",
        ];
        console.log(
            `%cTour is paused. Use %cplay()%c to continue.`,
            styles[0],
            styles[1],
            styles[0]
        );
        await new Promise((resolve) => {
            window.play = () => {
                resolve();
                delete window.play;
            };
        });
    }

    /**
     * @param {TourAction} action
     * @param {HTMLElement|true} anchor
     */
    async perform(action, anchor) {
        if (anchor === true) {
            return;
        }
        if (this.showPointer) {
            await hoot.waitFor(".o_tour_pointer", { timeout: action.timeout });
        }
        if (this.config.stepDelay > 0) {
            await hoot.delay(this.config.stepDelay);
        }
        if (anchor.disabled) {
            await hoot.waitUntil(() => !anchor.disabled, { timeout: 10000 });
        }
        if (!anchor.isConnected) {
            this.removeListeners();
            super.play(action.index);
            return;
        }
        this.allowUnload = false;
        if (action.expectUnloadPage) {
            this.allowUnload = true;
            setTimeout(() => {
                const message = `
                    The key { expectUnloadPage } is defined but page has not been unloaded within 20000 ms.
                    You probably don't need it.
                `.replace(/^\s+/gm, "");
                this.throwError(message);
            }, 20000);
        }
        await action.doAction(action.element);
        if (this.consumeEvents.length) {
            this.awaitingConsume = true;
            await this.consumed.promise;
            this.awaitingConsume = false;
        } else {
            this.currentActionIndex = action.index + 1;
        }
        if (this.debugMode) {
            console.log(anchor);
            console.log("This step has run successfully");
            if (action.pause) {
                await this.pause();
            }
        }
        tourState.setCurrentIndex(this.currentActionIndex);
        if (this.allowUnload) {
            return "StopTheMacro!";
        }
        super.play(this.currentActionIndex);
    }

    play() {
        this.removeListeners();
        pointerState.trigger = undefined;
        this.isLost = false;
        super.play(this.currentActionIndex);
    }

    setActionListeners() {
        if (!this.anchorEl) {
            this.removeListeners = () => {};
            return;
        }
        const element = this.currentAction.findTarget(this.anchorEl);
        this.consumeEvents = element ? this.currentAction.getConsumeEvents(element) : [];
        this.consumed = Promise.withResolvers();
        const cleanups = this.setupListeners({
            consumeEvents: this.consumeEvents,
            onConsume: ({ selectsDropdownItem }) => {
                if (selectsDropdownItem) {
                    this.skipNextActionIfDropdownItem();
                }
                this.currentActionIndex++;
                tourState.setCurrentIndex(this.currentActionIndex);
                this.next();
            },
            onError: () => {
                if (this.currentAction.event === "drop") {
                    this.currentActionIndex--;
                    this.next();
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

    skipNextActionIfDropdownItem() {
        const nextAction = this.actions.at(this.currentActionIndex + 1);
        if (nextAction?.findTrigger()?.closest(".o-autocomplete--dropdown-item")) {
            this.currentActionIndex++;
        }
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     */
    start(env) {
        TourEngine.removePointer();
        TourEngine.current?.stop();
        TourEngine.current = this;
        if (this.showPointer) {
            TourEngine.removePointer = this.overlay.add(
                TourPointer,
                { pointerState },
                { sequence: 1100 } // sequence based on bootstrap z-index values.
            );
        }
        if (this.mode === "auto") {
            window.addEventListener("beforeunload", () => {
                if (!this.allowUnload) {
                    const message = `
                        Be sure to use { expectUnloadPage: true } for any step
                        that involves firing a beforeUnload event.
                        This avoid a non-deterministic behavior by explicitly stopping
                        the tour that might continue before the page is unloaded.
                    `.replace(/^\s+/gm, "");
                    this.throwError(message);
                }
            });
        }
        this.currentActionIndex = tourState.getCurrentIndex();
        if (this.debugMode && this.currentActionIndex === 0) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
        if (this.isRobot) {
            setupEventActions(document.createElement("div"), { allowSubmit: true });
            enableEventLogs(this.debugMode);
            transitionConfig.disabled = true;
            this.hootNameSpace = hoot.exposeHelpers(hoot);
            console.debug(`Hoot DOM helpers available from \`window.${this.hootNameSpace}\``);
        }
        this.busController = new AbortController();
        const { signal } = this.busController;
        env.bus.addEventListener("ACTION_MANAGER:UPDATE", () => (this.isBusy = true), { signal });
        env.bus.addEventListener(
            "ACTION_MANAGER:UI-UPDATED",
            () => {
                this.isBusy = false;
                if (this.isLost && !this.currentAction.findTrigger()) {
                    this.backward();
                }
            },
            { signal }
        );
        this.currentIndex = this.currentActionIndex;
        super.start();
    }

    stop(error) {
        super.stop(error);
        this.removeListeners();
        this.detach();
    }

    /**
     * @param {string} [error]
     */
    throwError(...args) {
        console.groupEnd();
        tourState.setCurrentTourOnError();
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        console.dir(this.describeWhereIFailed);
        const error = [
            `FAILED: ${this.actions[this.currentActionIndex].describeMe}.`,
            ...args,
        ].join("\n");
        if (this.debugMode) {
            console.warn(error);
            // eslint-disable-next-line no-debugger
            debugger;
        } else {
            // console.error notifies the test runner that the tour failed.
            console.error(error);
        }
    }

    /**
     * @param {TourAction} action
     */
    track(action) {
        if (!action.active) {
            return true;
        }
        if (this.currentAction !== action) {
            this.enter(action);
        }
        const anchor = action.findTrigger();
        if (!action.event) {
            if (anchor && !this.isRobot) {
                console.log(`Step '${action.anchor}' ignored.`);
            }
            return anchor;
        }
        if (anchor) {
            this.isLost = false;
            if (anchor !== this.anchorEl) {
                this.removeListeners();
                this.anchorEl = anchor;
                this.setActionListeners();
                if (!this.isRobot && !this.consumeEvents.length) {
                    return true;
                }
            }
            this.updatePointer();
            return this.isRobot && anchor;
        } else if (this.anchorEl && !this.isRobot && !this.isLost) {
            if (
                !hoot.queryFirst(".o_home_menu", { visible: true }) &&
                !hoot.queryFirst(".dropdown-item.o_loading", { visible: true }) &&
                !this.isBusy
            ) {
                this.backward();
            } else {
                pointerState.trigger = undefined;
            }
        }
        return false;
    }

    updatePointer() {
        if (!this.showPointer) {
            return;
        }
        if (this.anchorEl) {
            pointerState.trigger = this.anchorEl;
            pointerState.content = this.currentAction.content || this.currentAction.defaultContent;
            pointerState.position = this.currentAction.tooltipPosition;
            pointerState.isZone = this.currentAction.event === "drop";
        } else {
            pointerState.trigger = undefined;
        }
    }
}
