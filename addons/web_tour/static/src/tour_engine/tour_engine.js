import * as hoot from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";
import { enableEventLogs, setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { Macro } from "@web/core/macro";
import { config as transitionConfig } from "@web/core/transition";
import { TourAction } from "@web_tour/tour_engine/tour_action";
import { TourObserver } from "@web_tour/tour_engine/tour_observer";
import { TourPointer, pointerState } from "@web_tour/tour_pointer/tour_pointer";
import { tourState } from "@web_tour/tour_state";

const SELECTOR_COMMANDS = ["check", "clear", "click", "dblclick", "hover", "uncheck"];
const POINTER_SELECTOR = ".o_tour_pointer:not(.o_tour_pointer_content)";

export class TourEngine extends Macro {
    static current = null;
    static removePointer = () => {};
    static MAX_BACKWARD_ACTIONS = 10;
    allowUnload = true;
    currentAction;
    currentActionIndex;
    currentTargetEl;
    consumeEvents = [];
    removeListeners = () => {};
    canSearch = true;
    searchedActionIndex = null;

    /**
     * Builds the actions of the tour from its steps, and the macro steps
     * looking for their trigger and, for the robot, performing them.
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
        this.showPointer = this.mode === "manual";
        this.actions = steps.flatMap((step) => this.buildActions(step));
        this.actions.forEach((action, index) => (action.index = index));
        this.steps = this.actions.map((action) => this.buildMacroStep(action));
        this.isBusy = false;
    }

    /**
     * Whether the tour runs in debug mode, which is the case unless `debug` is
     * explicitly disabled in its config: actions are logged in console groups,
     * and the debugger stops on the first action and on failures.
     * @returns {boolean}
     */
    get debugMode() {
        return this.config.debug !== false;
    }

    /**
     * The action being played when the tour fails: the robot may already have
     * moved {@link currentActionIndex} past the action it is performing, up to
     * the end of the tour.
     * @returns {TourAction}
     */
    get failedAction() {
        return this.currentAction ?? this.actions[this.currentActionIndex];
    }

    /**
     * Describes the failed action and the ones around it, the failed one being
     * framed, to locate a failure in the tour.
     * @returns {string}
     */
    get describeWhereIFailed() {
        const offset = 3;
        const currentIndex = this.failedAction.index;
        const start = Math.max(currentIndex - offset, 0);
        const end = Math.min(currentIndex + offset, this.actions.length - 1);
        const result = [];
        for (let i = start; i <= end; i++) {
            const action = this.actions[i];
            const text = [action.stringify];
            if (i === currentIndex) {
                const line = "-".repeat(10);
                const failing_step = `${line} FAILED: ${this.describeAction(action)} ${line}`;
                text.unshift(failing_step);
                text.push("-".repeat(failing_step.length));
            }
            result.push(...text);
        }
        return result.join("\n");
    }

    /**
     * Moves the tour back to the closest previous action whose trigger is in the
     * DOM, looking at most {@link TourEngine.MAX_BACKWARD_ACTIONS} actions back.
     */
    backward() {
        const fromIndex = Math.max(this.currentActionIndex - TourEngine.MAX_BACKWARD_ACTIONS, 0);
        for (let index = this.currentActionIndex - 1; index >= fromIndex; index--) {
            const action = this.actions[index];
            if (action.active && action.event && action.target.find()) {
                this.currentActionIndex = index;
                this.resume();
                return;
            }
        }
    }

    /**
     * Builds the actions played for the given step. The robot plays a whole
     * step in a single action, while a human plays each command of its `run`
     * as its own action.
     * @param {import("./tour_action").TourStep} step
     * @returns {TourAction[]}
     */
    buildActions(step) {
        if (this.isRobot) {
            return [this.buildRobotAction(step)];
        }
        return this.buildHumanActions(step);
    }

    /**
     * Builds the actions a human plays for the given step, one for each command
     * of its `run` (e.g. "drag" then "drop" for `drag_and_drop`). A step without
     * a `run` string, which a human can't perform, gives a single action only
     * waiting for its trigger.
     * @param {import("./tour_action").TourStep} step
     * @returns {TourAction[]}
     */
    buildHumanActions(step) {
        if (typeof step.run !== "string") {
            return [this.createAction(step, null, step.trigger)];
        }
        return this.parseRunCommands(step).map((command) =>
            this.createAction(step, command.event, command.targetSelector)
        );
    }

    /**
     * Builds the macro step playing the given action: its trigger looks for the
     * target of the action, and for the robot, its action performs it once the
     * target is found.
     * @param {TourAction} action
     * @returns {{
     *     trigger: () => HTMLElement|boolean,
     *     timeout: number,
     *     action?: (targetEl: HTMLElement|true) => Promise<string|undefined>,
     * }}
     */
    buildMacroStep(action) {
        const macroStep = {
            trigger: () => {
                if (!this.shouldSearch(action.index)) {
                    return false;
                }
                return this.trackAction(action);
            },
            timeout: action.timeout,
        };
        const isPerformedByRobot = this.isRobot && Boolean(action.event);
        if (isPerformedByRobot) {
            macroStep.action = (targetEl) => this.performAction(action, targetEl);
        }
        return macroStep;
    }

    /**
     * Builds the single action the robot plays for the given step: it waits for
     * the trigger of the step, then runs the whole `run`. Its events are the ones
     * of the "drop" of `drag_and_drop`, which a human must perform on the drop
     * zone, or else of the first command of `run`, listened on the element the
     * command acts on when it isn't the trigger (e.g. `click .other`).
     * @param {import("./tour_action").TourStep} step
     * @returns {TourAction}
     */
    buildRobotAction(step) {
        if (!step.run) {
            return this.createAction(step, null, step.trigger);
        }
        if (typeof step.run !== "string") {
            return this.createAction(step, "run", step.trigger);
        }
        const commands = this.parseRunCommands(step);
        const [firstCommand] = commands;
        const listenedCommand = commands.find(({ event }) => event === "drop") || firstCommand;
        if (listenedCommand === firstCommand && firstCommand.targetSelector === step.trigger) {
            return this.createAction(step, firstCommand.event, step.trigger);
        }
        return this.createAction(
            step,
            firstCommand.event,
            step.trigger,
            listenedCommand.event,
            listenedCommand.targetSelector
        );
    }

    /**
     * Creates an action of this tour for the given step.
     * @param {import("./tour_action").TourStep} step
     * @param {string|null} event
     * @param {string} targetSelector
     * @param {string} [listenedEvent]
     * @param {string} [listenedSelector]
     * @returns {TourAction}
     */
    createAction(step, event, targetSelector, listenedEvent, listenedSelector) {
        return new TourAction(
            step,
            event,
            targetSelector,
            listenedEvent,
            listenedSelector,
            this.mode,
            this.isRobot,
            this.debugMode,
            this.config.stepDelay || 0
        );
    }

    /**
     * Short description of the given action, with its position in the tour, used
     * in the logs and the errors.
     * @param {TourAction} action
     * @returns {string}
     */
    describeAction(action) {
        return (
            `[${action.index + 1}/${this.actions.length}] Tour ${this.name} → Step ` +
            (action.step.content
                ? `${action.step.content} (trigger: ${action.step.trigger})`
                : action.step.trigger)
        );
    }

    /**
     * Stops listening to the action manager, to the page unload and to the DOM
     * changes, and unregisters this tour as the current one.
     */
    detach() {
        this.listenersController?.abort();
        this.observer?.disconnect();
        if (TourEngine.current === this) {
            TourEngine.current = null;
        }
    }

    /**
     * Cleans up once the tour is over: removes the pointer and the tour state.
     * For the robot, also undoes its setup (see {@link teardownRobot}).
     */
    end() {
        this.detach();
        TourEngine.removePointer();
        pointerState.trigger = undefined;
        tourState.clear();
        this.teardownRobot();
    }

    /**
     * For the robot, silences the errors raised once its tour has been reported
     * as succeeded or failed.
     */
    ignoreErrors() {
        if (!this.isRobot) {
            return;
        }
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
     * Makes the given action the current one: removes the listeners of the
     * previous one, saves its index in the tour state and logs it. In debug
     * mode, the action is logged in a collapsed console group along with its
     * step, stopping in the debugger when the step defines `break`.
     * @param {TourAction} action
     */
    enterAction(action) {
        this.removeListeners();
        this.currentAction = action;
        this.currentActionIndex = action.index;
        tourState.setCurrentIndex(action.index);
        if (this.debugMode) {
            console.groupEnd();
            console.groupCollapsed(this.describeAction(action));
            console.log(action.stringify);
            if (action.step.break) {
                // eslint-disable-next-line no-debugger
                debugger;
            }
        } else {
            console.log(this.describeAction(action));
        }
    }

    /**
     * Moves on once the current action has been consumed: for the robot, resolves
     * the promise {@link performAction} is waiting for, while for a human, the macro is
     * resumed from the new current action.
     */
    next() {
        if (this.isRobot) {
            this.removeListeners();
            this.consumed.resolve();
        } else {
            this.resume();
        }
    }

    /**
     * Called by the macro once every action is done: ends the tour and logs the
     * success. In manual mode, also shows its rainbow man if any, which the robot
     * fails without, marks the tour as consumed and starts the next one, if any.
     */
    async onComplete() {
        if (this.debugMode) {
            console.groupEnd();
        }
        let message = this.config.rainbowManMessage || this.rainbowManMessage;
        if (message && window.DOMPurify && this.mode === "manual") {
            message = window.DOMPurify.sanitize(message);
            this.effect.add({
                type: "rainbow_man",
                message: markup(message),
            });
            if (this.isRobot) {
                this.awaitingRainbowMan = true;
                try {
                    await hoot.waitFor(".o_reward_rainbow_man", { timeout: 10000 });
                } catch (error) {
                    this.onError({ error });
                    return;
                }
                this.awaitingRainbowMan = false;
            }
        }
        this.end();
        console.log("tour succeeded");
        // Used to see easily in the python console and to know which tour has been succeeded in suite tours case.
        const succeeded = `║ TOUR ${this.name} SUCCEEDED ║`;
        const msg = [succeeded];
        msg.unshift("╔" + "═".repeat(succeeded.length - 2) + "╗");
        msg.push("╚" + "═".repeat(succeeded.length - 2) + "╝");
        console.log(`\n\n${msg.join("\n")}\n`);
        this.ignoreErrors();

        if (this.mode === "manual") {
            const nextTour = await this.orm.call("web_tour.tour", "consume", [this.name]);
            if (nextTour) {
                this.onChainNextTour(nextTour);
            }
        }
    }

    /**
     * Called by the macro when it fails, e.g. when the trigger of an action isn't
     * found in time: reports the failure, with the reasons why the trigger
     * couldn't be used or what the robot was still waiting for, and ends the
     * tour.
     * @param {Object} params
     * @param {Error & { type?: string }} params.error
     */
    onError({ error }) {
        this.removeListeners();
        const errors = error.type === "Timeout" ? [...this.failedAction.target.error] : [];
        if (this.awaitingPointer) {
            errors.push(`BUT: the pointer has not been displayed on the element.`);
        }
        if (this.awaitingConsume) {
            const names = this.consumeEvents.map((c) => c.name).join(", ");
            errors.push(`BUT: the action has been performed without triggering (${names}).`);
        }
        if (this.awaitingPointerRemoval) {
            errors.push(`BUT: the pointer has not been removed after the action.`);
        }
        if (this.awaitingRainbowMan) {
            errors.push(`BUT: the rainbow man has not been displayed.`);
        }
        this.throwError(...errors, error.message);
        this.end();
        this.ignoreErrors();
    }

    /**
     * Splits the `run` string of the given step into its commands, each with the
     * event to perform and the selector of the element it is performed on: the
     * argument of the command when it is a selector (e.g. `click .other`), the
     * drop zone for the "drop" of `drag_and_drop`, or the trigger of the step.
     * @param {import("./tour_action").TourStep} step
     * @returns {{ event: string, targetSelector: string }[]}
     */
    parseRunCommands(step) {
        const commands = [];
        for (const todo of step.run.split("&&")) {
            const match = String(todo)
                .trim()
                .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
            const command = match.groups?.action;
            const argument = match.groups?.arguments;
            if (command === "drag_and_drop") {
                commands.push({ event: "drag", targetSelector: step.trigger });
                commands.push({ event: "drop", targetSelector: argument || step.trigger });
            } else if (SELECTOR_COMMANDS.includes(command) && argument) {
                commands.push({ event: command, targetSelector: argument });
            } else {
                commands.push({ event: command, targetSelector: step.trigger });
            }
        }
        return commands;
    }

    /**
     * Pauses the tour until `play()` is called from the console, after an action
     * whose step defines `pause` in debug mode.
     * @returns {Promise<void>}
     */
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
     * Performs the given action as the robot, once its target is found: waits
     * for the pointer, the step delay and the target to be enabled, runs the
     * action, then, in manual mode, waits for the events consuming it and for
     * its pointer to be removed before playing the macro from the next action.
     * The action is looked for again if its target left the DOM meanwhile, and
     * nothing is done for an inactive action, nor once the tour is stopped.
     * @param {TourAction} action
     * @param {HTMLElement|true} targetEl
     * @returns {Promise<string|undefined>} a truthy value stopping the macro when
     *     the page is expected to unload
     */
    async performAction(action, targetEl) {
        if (targetEl === true) {
            return;
        }
        if (this.pointsTo(action)) {
            this.awaitingPointer = true;
            await hoot.waitUntil(() => !targetEl.isConnected || hoot.queryFirst(POINTER_SELECTOR), {
                timeout: action.timeout,
            });
            this.awaitingPointer = false;
        }
        if (this.config.stepDelay > 0) {
            await hoot.delay(this.config.stepDelay);
        }
        if (targetEl.disabled) {
            await hoot.waitUntil(() => !targetEl.disabled, { timeout: 10000 });
        }
        if (this.isComplete) {
            return;
        }
        if (!targetEl.isConnected) {
            this.removeListeners();
            super.play(action.index);
            return;
        }
        this.allowUnload = false;
        if (action.step.expectUnloadPage) {
            this.allowUnload = true;
            setTimeout(() => {
                const message = `
                    The key { expectUnloadPage } is defined but page has not been unloaded within 20000 ms.
                    You probably don't need it.
                `.replace(/^\s+/gm, "");
                this.throwError(message);
            }, 20000);
        }
        await action.doAction(action.target.matchedEl);
        if (this.consumeEvents.length) {
            this.awaitingConsume = true;
            await this.consumed.promise;
            this.awaitingConsume = false;
        } else {
            this.currentActionIndex = action.index + 1;
        }
        if (this.isComplete) {
            return;
        }
        if (this.pointsTo(action)) {
            pointerState.trigger = undefined;
            this.awaitingPointerRemoval = true;
            await hoot.waitUntil(() => !hoot.queryFirst(POINTER_SELECTOR), {
                timeout: action.timeout,
            });
            this.awaitingPointerRemoval = false;
        }
        if (this.debugMode) {
            console.log(targetEl);
            console.log("This step has run successfully");
            if (action.step.pause) {
                await this.pause();
            }
        }
        if (this.isComplete) {
            return;
        }
        tourState.setCurrentIndex(this.currentActionIndex);
        if (this.allowUnload) {
            return "StopTheMacro!";
        }
        super.play(this.currentActionIndex);
    }

    /**
     * Whether the pointer is shown on the target of the given action: in manual
     * mode, unless the action runs a function, which a human isn't pointed to.
     * @param {TourAction} action
     * @returns {boolean}
     */
    pointsTo(action) {
        return this.showPointer && action.event !== "run";
    }

    /**
     * Plays the macro from the current action, after removing the listeners and
     * the pointer of the previous one.
     */
    resume() {
        this.removeListeners();
        pointerState.trigger = undefined;
        this.canSearch = true;
        super.play(this.currentActionIndex);
    }

    /**
     * In manual mode, listens to the events consuming the current action, on its
     * target or on its listened target when it has one: once one of them is
     * triggered, the tour moves on to the next action. A drop outside of the
     * expected zone moves back to the drag action. An automatic tour doesn't wait
     * for these events, its robot moves on as soon as the action is done.
     */
    setActionListeners() {
        const listenedEl =
            this.mode === "manual" &&
            (this.currentAction.listenedTarget
                ? this.currentAction.listenedTarget.find()
                : this.currentTargetEl);
        this.consumeEvents = listenedEl ? this.currentAction.getConsumeEvents(listenedEl) : [];
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
            this.currentTargetEl = undefined;
            while (cleanups.length) {
                cleanups.pop()();
            }
        };
    }

    /**
     * Adds a capturing listener for each of the given consume events, calling
     * `onConsume` when the event fulfills its condition, and `onError` otherwise.
     * @param {Object} params
     * @param {import("./tour_action").ConsumeEvent[]} params.consumeEvents
     * @param {(consumeEvent: import("./tour_action").ConsumeEvent) => any} params.onConsume
     * @param {() => any} [params.onError]
     * @returns {(() => void)[]} the cleanups removing the listeners
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
     * Called on every animation frame by the macro. In manual mode, the trigger
     * of a newly played action is looked for right away, then only once
     * {@link TourObserver} flagged that the DOM may have changed.
     * @param {number} index
     * @returns {boolean}
     */
    shouldSearch(index) {
        if (this.mode === "auto") {
            return true;
        }
        if (!this.canSearch && index === this.searchedActionIndex) {
            return false;
        }
        this.canSearch = false;
        this.searchedActionIndex = index;
        return true;
    }

    /**
     * Skips the next action when it clicks on an autocomplete dropdown item, as
     * the current action already selected one (e.g. by pressing Enter).
     */
    skipNextActionIfDropdownItem() {
        const nextAction = this.actions.at(this.currentActionIndex + 1);
        if (nextAction?.target.find()?.closest(".o-autocomplete--dropdown-item")) {
            this.currentActionIndex++;
        }
    }

    /**
     * Starts the tour from the action index saved in the tour state: sets up the
     * DOM observer in manual mode, the pointer, the hoot helpers and the unload
     * check for the robot, then starts the macro.
     * @param {import("@web/env").OdooEnv} env
     */
    start(env) {
        TourEngine.removePointer();
        TourEngine.current?.stop();
        TourEngine.current = this;
        if (this.mode === "manual") {
            this.observer = new TourObserver(() => (this.canSearch = true));
            this.observer.start(document);
        }
        if (this.showPointer) {
            TourEngine.removePointer = this.overlay.add(
                TourPointer,
                { pointerState },
                { sequence: 1100 } // sequence based on bootstrap z-index values.
            );
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
        this.listenersController = new AbortController();
        const { signal } = this.listenersController;
        env.bus.addEventListener("ACTION_MANAGER:UPDATE", () => (this.isBusy = true), { signal });
        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", () => (this.isBusy = false), {
            signal,
        });
        if (this.isRobot) {
            window.addEventListener(
                "beforeunload",
                () => {
                    if (!this.allowUnload) {
                        const message = `
                            Be sure to use { expectUnloadPage: true } for any step
                            that involves firing a beforeUnload event.
                            This avoid a non-deterministic behavior by explicitly stopping
                            the tour that might continue before the page is unloaded.
                        `.replace(/^\s+/gm, "");
                        this.throwError(message);
                    }
                },
                { signal }
            );
        }
        this.currentIndex = this.currentActionIndex;
        super.start();
    }

    /**
     * Stops the macro, then the tour, removing its pointer and all its listeners
     * and undoing the setup of its robot. Does nothing once the tour is stopped,
     * as another tour may have been started since.
     * @param {Error} [error]
     */
    stop(error) {
        if (this.isComplete) {
            return;
        }
        super.stop(error);
        pointerState.trigger = undefined;
        this.removeListeners();
        this.detach();
        this.teardownRobot();
    }

    /**
     * Undoes what {@link start} sets up for the robot: removes the exposed hoot
     * helpers and enables the transitions again.
     */
    teardownRobot() {
        if (!this.isRobot) {
            return;
        }
        delete window[this.hootNameSpace];
        transitionConfig.disabled = false;
    }

    /**
     * Reports the failure of the current action, with the given details and the
     * actions around it. The test runner is notified through `console.error`,
     * while debug mode logs a warning and stops in the debugger instead.
     * @param {...string} args
     */
    throwError(...args) {
        console.groupEnd();
        tourState.setCurrentTourOnError();
        // The logged text shows the relative position of the failed step.
        // Useful for finding the failed step.
        console.dir(this.describeWhereIFailed);
        const error = [`FAILED: ${this.describeAction(this.failedAction)}.`, ...args].join("\n");
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
     * Looks for the target of the given action, called by the macro on every
     * search. For the robot, returns the target once found, so that the macro
     * performs the action. For a human, points to the target and listens to the
     * events consuming the action, going back to a previous action when the
     * target is lost while the UI isn't busy.
     * @param {TourAction} action
     * @returns {HTMLElement|boolean} truthy when the macro can move on
     */
    trackAction(action) {
        if (!action.active) {
            return true;
        }
        if (this.currentAction !== action) {
            this.enterAction(action);
        }
        const targetEl = action.target.find();
        if (!action.event) {
            if (targetEl && !this.isRobot) {
                console.log(`Step '${action.target.selector}' ignored.`);
            }
            return targetEl;
        }
        if (targetEl) {
            if (targetEl !== this.currentTargetEl) {
                this.removeListeners();
                this.currentTargetEl = targetEl;
                this.setActionListeners();
                if (!this.isRobot && !this.consumeEvents.length) {
                    return true;
                }
            }
            this.updatePointer();
            return this.isRobot && targetEl;
        } else if (this.currentTargetEl && !this.isRobot) {
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

    /**
     * Points to the target of the current action with its content and position,
     * or hides the pointer when there is no target. Does nothing when the
     * current action isn't pointed to (see {@link pointsTo}).
     */
    updatePointer() {
        if (!this.pointsTo(this.currentAction)) {
            return;
        }
        if (this.currentTargetEl) {
            pointerState.trigger = this.currentTargetEl;
            pointerState.content =
                this.currentAction.step.content || this.currentAction.defaultContent;
            pointerState.position = this.currentAction.step.tooltipPosition;
            pointerState.isZone = this.currentAction.event === "drop";
        } else {
            pointerState.trigger = undefined;
        }
    }
}
